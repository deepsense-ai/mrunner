# -*- coding: utf-8 -*-
import logging
import re

import yaml
from kubernetes import client, config

from mrunner.experiment import Experiment
from mrunner.utils import GeneratedTemplateFile, DObject

LOGGER = logging.getLogger(__name__)


class K8sConfiguration(GeneratedTemplateFile):
    DEFAULT_K8S_CONFIG_TEMPLATE = 'job.yaml.jinja2'
    RESOURCE_NAME_MAP = {'cpu': 'cpu', 'mem': 'memory', 'gpu': 'nvidia.com/gpu', 'tpu': 'cloud-tpus.google.com/v2'}

    def __init__(self, context, experiment, jobs):
        context.limits = dict([self._map_resources(*res.split('=')) for res in context.resources.split(' ')])
        super(K8sConfiguration, self).__init__(template_filename=self.DEFAULT_K8S_CONFIG_TEMPLATE,
                                               context=context, experiment=experiment, jobs=jobs)

    def _map_resources(self, resource_name, resource_qty):
        name = self.RESOURCE_NAME_MAP[resource_name]
        if name == 'memory':
            qty = resource_qty + 'i'
        else:
            qty = resource_qty
        return name, qty


class ExperimentRunOnKubernetes(Experiment):

    @property
    def pvc_name(self):
        return KubernetesBackend.NFS_PVC_NAME

    @property
    def namespace(self):
        return re.sub(r'[ .,_-]+', '-', self.project_name)


class Job(DObject):

    @classmethod
    def create(cls, image, context, experiment):
        env = context.env.to_dict().copy()
        env.update(experiment.all_env)
        env = {k: str(v) for k, v in env.items()}
        return cls(context=context, experiment=experiment, image=image, env=env,
                   labels=[], node_selector=[])

    @staticmethod
    def _escape_arg(arg):
        return arg \
            .replace('.', '') \
            .replace('--', '') \
            .replace('_', '') \
            .replace('=', '')

    @property
    def name(self):
        from namesgenerator import get_random_name
        experiment_name = re.sub(r'[ ,.\-_:;]+', '-', self.experiment.name)
        return '{}-{}'.format(experiment_name, get_random_name('-'))


class StandardPVC(client.V1PersistentVolumeClaim):

    def __init__(self, name, size, access_mode):
        resource_req = client.V1ResourceRequirements(requests={'storage': size + 'i'})
        pvc_spec = client.V1PersistentVolumeClaimSpec(access_modes=[access_mode], resources=resource_req)
        super(StandardPVC, self).__init__(metadata=client.V1ObjectMeta(name=name), spec=pvc_spec)


class NFSPod(client.V1Pod):
    """
    Pod which contains NFS server to share mounted volume
    See details on https://github.com/kubernetes/examples/tree/master/staging/volumes/nfs
    """
    PORTS = {'nfs': 2049, 'mountd': 20048, 'rpcbind': 111}
    LABELS = {'role': 'nfs-server'}
    IMAGE = 'k8s.gcr.io/volume-nfs:0.8'

    def __init__(self, name, storage_pvc):
        internal_volume_name = 'nfs-server-volume'
        mount_path = '/exports'

        ctr = client.V1Container(name=name, image=self.IMAGE,
                                 ports=[client.V1ContainerPort(name=k, container_port=v)
                                        for k, v in self.PORTS.items()],
                                 security_context=client.V1SecurityContext(privileged=True),
                                 volume_mounts=[client.V1VolumeMount(mount_path=mount_path, name=internal_volume_name)])
        volume_source = client.V1PersistentVolumeClaimVolumeSource(claim_name=storage_pvc)
        volume = client.V1Volume(name=internal_volume_name, persistent_volume_claim=volume_source)
        pod_spec = client.V1PodSpec(containers=[ctr], volumes=[volume])
        metadata = client.V1ObjectMeta(name=name, labels=self.LABELS)
        super(NFSPod, self).__init__(metadata=metadata, spec=pod_spec)


class NFSSvc(client.V1Service):
    """
    Service for NFS pod
    """

    def __init__(self, name):
        nfs_service_spec = client.V1ServiceSpec(ports=[client.V1ServicePort(name=k, port=v)
                                                       for k, v in NFSPod.PORTS.items()],
                                                selector=NFSPod.LABELS)
        super(NFSSvc, self).__init__(metadata=client.V1ObjectMeta(name=name), spec=nfs_service_spec)


class NFSPv(client.V1PersistentVolume):
    """
    Persistent volume which wraps NFS server.
    Provide PV with ReadWriteMany access mode, which is required to provide storage for pods
    scheduled on different nodes
    See details on https://github.com/kubernetes/examples/tree/master/staging/volumes/nfs
    """
    STORAGE_CLASS = 'nfs'

    def __init__(self, name, nfs_server_ip):
        pv_spec = client.V1PersistentVolumeSpec(capacity={'storage': '1Mi'},
                                                access_modes=['ReadWriteMany'],
                                                storage_class_name=self.STORAGE_CLASS,
                                                persistent_volume_reclaim_policy='Delete',
                                                nfs=client.V1NFSVolumeSource(server=nfs_server_ip, path='/'))
        super(NFSPv, self).__init__(metadata=client.V1ObjectMeta(name=name), spec=pv_spec)


class NFSPvc(client.V1PersistentVolumeClaim):
    """
    Persistent Volume Claim - claim which attaches to NFS PV
    """

    def __init__(self, name):
        resource_req = client.V1ResourceRequirements(requests={'storage': '1Mi'})
        pvc_spec = client.V1PersistentVolumeClaimSpec(access_modes=['ReadWriteMany'],
                                                      resources=resource_req,
                                                      storage_class_name=NFSPv.STORAGE_CLASS)
        super(NFSPvc, self).__init__(metadata=client.V1ObjectMeta(name=name), spec=pvc_spec)


class KubernetesBackend(object):
    DEFAULT_STORAGE_PVC_SIZE = '40G'
    DEFAULT_STORAGE_PVC_NAME = 'storage'
    NFS_PVC_NAME = 'nfs'

    def __init__(self, context):
        self._check_env()
        self._context = context
        config.load_kube_config()
        self.api = client.CoreV1Api()

    def run(self, image, experiment):
        experiment = ExperimentRunOnKubernetes(**experiment.to_dict())
        self.configure_namespace(experiment)
        self.configure_storage_for_project(experiment)

        jobs = [Job.create(image=image, context=self._context, experiment=experiment), ]

        # TODO: [PZ] use kubernetes python client to create dictionaries in code
        k8s_jobs_conf_file = K8sConfiguration(self._context, experiment, jobs=jobs)
        with open(k8s_jobs_conf_file.path, 'r') as conf_file:
            jobs_structures = [yaml.load(conf_file), ]

        self.api = client.BatchV1Api()
        for job in jobs_structures:
            # metadata = client.V1ObjectMeta(name='job.gke-sandbox.cnn-adv.epochs-2')
            # volume = client.V1Volume(name='experiment-storage',
            #                          persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
            #                              claim_name='pvc.gke-sandbox'))
            # container = client.V1Container(name='job.gke-sandbox.cnn-adv.epochs-2',
            #                                image='gcr.io/gke-sandbox-200208/cnn_adv:20180405_095303',
            #                                args=['--epochs', '2'],
            #                                volume_mounts=client.V1VolumeMount(mount_path='/storage',
            #                                                                   name='experiment-storage'),
            #                                resources=client.V1ResourceRequirements(
            #                                    limits=client.V1LimitRangeSpec(limits={'cpu': '200m'})),
            #                                env=[client.V1EnvVar(name='NEPTUNE_HOST', value='kdmi.neptune.deepsense.io'),
            #                                     client.V1EnvVar(name='NEPTUNE_USER',
            #                                                     value='pawel.ziecina@codilime.com'),
            #                                     client.V1EnvVar(name='NEPTUNE_PORT', value='443'),
            #                                     client.V1EnvVar(name='NEPTUNE_PASSWORD', value='koh1fei2Aif6meud'),
            #                                     client.V1EnvVar(name='MRUNNER_UNDER_NEPTUNE', value='1')])
            #
            # pod_spec = client.V1PodTemplateSpec(spec=client.V1PodSpec(restart_policy='Never', containers=[container],
            #                                                           volumes=[volume]))
            # j = client.V1Job(api_version='batch/v1', kind='Job', metadata=metadata,
            #                  spec=client.V1JobSpec(template=pod_spec))
            # json.dump(j.to_dict(), open('/tmp/j_ref.json', 'w'), indent=2)
            # json.dump(job, open('/tmp/j.json', 'w'), indent=2)
            self.api.create_namespaced_job(body=job, namespace=experiment.namespace)

    def configure_namespace(self, experiment):
        namespace = client.V1Namespace(metadata=client.V1ObjectMeta(name=experiment.namespace))
        self._ensure_resource('namespace', None, experiment.namespace, namespace)

    def configure_storage_for_project(self, experiment):
        """Configures storage as in https://github.com/kubernetes/examples/tree/master/staging/volumes/nfs"""
        nfs_svc_name = 'nfs-server'
        nfs_pv_name = 'pvc-nfs-{}'.format(experiment.namespace)

        self._ensure_resource('pvc', experiment.namespace, self.DEFAULT_STORAGE_PVC_NAME,
                              StandardPVC(name=self.DEFAULT_STORAGE_PVC_NAME,
                                          size=self._context.default_pvc_size or self.DEFAULT_STORAGE_PVC_SIZE,
                                          access_mode="ReadWriteOnce"))
        self._ensure_resource('pod', experiment.namespace, nfs_svc_name,
                              NFSPod(name=nfs_svc_name, storage_pvc=self.DEFAULT_STORAGE_PVC_NAME))
        _, nfs_svc = self._ensure_resource('svc', experiment.namespace, nfs_svc_name, NFSSvc(name=nfs_svc_name))

        nfs_svc_ip = nfs_svc.spec.cluster_ip
        _, nfs_pv = self._ensure_resource('pv', None, nfs_pv_name, NFSPv(nfs_pv_name, nfs_svc_ip))
        if nfs_pv.spec.nfs.server != nfs_svc_ip:
            nfs_pv.spec.source.server = nfs_svc_ip
            self.api.patch_persistent_volume(nfs_pv_name, nfs_pv)
        self._ensure_resource('pvc', experiment.namespace, self.NFS_PVC_NAME, NFSPvc(name=self.NFS_PVC_NAME))

    def _ensure_resource(self, resource_type, namespace, name, resource_body):
        list_kwargs = {'field_selector': 'metadata.name={}'.format(name)}
        create_kwargs = {'body': resource_body}

        if namespace:
            list_kwargs['namespace'] = namespace
            create_kwargs['namespace'] = namespace

        list_fun, create_fun = {
            'pod': (self.api.list_namespaced_pod, self.api.create_namespaced_pod),
            'pv': (self.api.list_persistent_volume, self.api.create_persistent_volume),
            'pvc': (self.api.list_namespaced_persistent_volume_claim,
                    self.api.create_namespaced_persistent_volume_claim),
            'svc': (self.api.list_namespaced_service, self.api.create_namespaced_service),
            'namespace': (self.api.list_namespace, self.api.create_namespace),
        }[resource_type]
        response = list_fun(**list_kwargs)
        if not response.items:
            resource = create_fun(**create_kwargs)
            LOGGER.debug('{}/{} created ({})'.format(resource_type, name, resource.to_str()))
        else:
            resource = response.items[0]
            LOGGER.debug('{}/{} exists'.format(resource_type, name))
        return bool(response.items), resource

    def _check_env(self):
        import subprocess

        try:
            from subprocess import DEVNULL  # py3k
        except ImportError:
            import os
            DEVNULL = open(os.devnull, 'wb')

        result = 0
        for cmd, link in [('kubectl', 'https://kubernetes.io/docs/tasks/tools/install-kubectl'),
                          ('gcloud', 'https://cloud.google.com/sdk/docs/quickstarts')]:
            try:
                subprocess.call(cmd, stdout=DEVNULL, stderr=DEVNULL)
            except OSError as e:
                raise RuntimeError('Missing {} cmd. Please install and setup it first: {}'.format(cmd, link))
        return result
