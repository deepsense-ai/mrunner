# -*- coding: utf-8 -*-
import logging
import re

from kubernetes import client, config

from mrunner.experiment import Experiment

LOGGER = logging.getLogger(__name__)


class ExperimentRunOnKubernetes(Experiment):

    @property
    def namespace(self):
        return re.sub(r'[ .,_-]+', '-', self.project_name)


class Job(client.V1Job):
    RESOURCE_NAME_MAP = {'cpu': 'cpu', 'mem': 'memory', 'gpu': 'nvidia.com/gpu', 'tpu': 'cloud-tpus.google.com/v2'}

    def __init__(self, image, context, experiment):
        from namesgenerator import get_random_name

        experiment_name = re.sub(r'[ ,.\-_:;]+', '-', experiment.name)
        name = '{}-{}'.format(experiment_name, get_random_name('-'))

        envs = context.env.to_dict().copy()
        envs.update(experiment.all_env)
        envs = {k: str(v) for k, v in envs.items()}
        resources = context.resources or ''
        resources = dict([self._map_resources(*r.split('=')) for r in resources.split(' ') if r])
        internal_volume_name = 'experiment-storage'

        vol = client.V1Volume(name=internal_volume_name,
                              persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                                  claim_name=KubernetesBackend.NFS_PVC_NAME))
        ctr = client.V1Container(name=name, image=image, args=experiment.params,
                                 volume_mounts=[client.V1VolumeMount(mount_path=context.storage,
                                                                     name=internal_volume_name)],
                                 resources=client.V1ResourceRequirements(
                                     limits={k: v for k, v in resources.items()}),
                                 env=[client.V1EnvVar(name=k, value=v) for k, v in envs.items()])
        pod_spec = client.V1PodSpec(restart_policy='Never', containers=[ctr], volumes=[vol])
        pod_template = client.V1PodTemplateSpec(spec=pod_spec)
        job_spec = client.V1JobSpec(template=pod_template)
        super(Job, self).__init__(metadata=client.V1ObjectMeta(name=name), spec=job_spec)

    def _map_resources(self, resource_name, resource_qty):
        name = self.RESOURCE_NAME_MAP[resource_name]
        if name == 'memory':
            qty = resource_qty + 'i'
        else:
            qty = resource_qty
        return name, qty

    @staticmethod
    def _escape_arg(arg):
        return re.sub(r'[ .,_=-]+', '-', arg)


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
        self.core_api = client.CoreV1Api()
        self.batch_api = client.BatchV1Api()

    def run(self, image, experiment):
        experiment = ExperimentRunOnKubernetes(**experiment.to_dict())

        self.configure_namespace(experiment)
        self.configure_storage_for_project(experiment)

        for experiment in [experiment, ]:
            job = Job(image, self._context, experiment)
            job_name = job.to_dict()['metadata']['name']
            self._ensure_resource('job', experiment.namespace, job_name, job)

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
            self.core_api.patch_persistent_volume(nfs_pv_name, nfs_pv)
            LOGGER.warning('pv/{}: patched NFS server ip (current={})', nfs_pv_name, nfs_svc_ip)
        self._ensure_resource('pvc', experiment.namespace, self.NFS_PVC_NAME, NFSPvc(name=self.NFS_PVC_NAME))

    def _ensure_resource(self, resource_type, namespace, name, resource_body):
        list_kwargs = {'field_selector': 'metadata.name={}'.format(name)}
        create_kwargs = {'body': resource_body}

        if namespace:
            list_kwargs['namespace'] = namespace
            create_kwargs['namespace'] = namespace

        list_fun, create_fun = {
            'job': (self.batch_api.list_namespaced_job, self.batch_api.create_namespaced_job),
            'namespace': (self.core_api.list_namespace, self.core_api.create_namespace),
            'pod': (self.core_api.list_namespaced_pod, self.core_api.create_namespaced_pod),
            'pv': (self.core_api.list_persistent_volume, self.core_api.create_persistent_volume),
            'pvc': (self.core_api.list_namespaced_persistent_volume_claim,
                    self.core_api.create_namespaced_persistent_volume_claim),
            'svc': (self.core_api.list_namespaced_service, self.core_api.create_namespaced_service),
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
