# -*- coding: utf-8 -*-
import re

import yaml
from kubernetes import client, config

from mrunner.experiment import Experiment
from mrunner.utils import GeneratedTemplateFile, DObject


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
        return 'nfs'

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


class KubernetesBackend(object):
    DEFAULT_PVC_SIZE = '40G'
    DEFAULT_NFS_PVC_NAME = 'storage'

    def __init__(self, context):
        check_env()
        self._context = context
        config.load_kube_config()

    def run(self, image, experiment):
        experiment = ExperimentRunOnKubernetes(**experiment.to_dict())
        self._ensure_namespace(experiment)
        self._ensure_pvc(experiment)
        jobs = [Job.create(image=image, context=self._context, experiment=experiment), ]

        # TODO: [PZ] use kubernetes python client to create dictionaries in code
        k8s_jobs_conf_file = K8sConfiguration(self._context, experiment, jobs=jobs)
        with open(k8s_jobs_conf_file.path, 'r') as conf_file:
            jobs_structures = [yaml.load(conf_file), ]

        api = client.BatchV1Api()
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
            api.create_namespaced_job(body=job, namespace=experiment.namespace)

    def _ensure_namespace(self, experiment):
        api = client.CoreV1Api()
        field_selector = 'metadata.name={}'.format(experiment.namespace)
        response = api.list_namespace(field_selector=field_selector)
        if not response.items:
            api.create_namespace(body=client.V1Namespace(metadata=client.V1ObjectMeta(name=experiment.namespace)))

    def _ensure_pvc(self, experiment):
        api = client.CoreV1Api()
        field_selector = 'metadata.name={}'.format(experiment.pvc_name)
        response = api.list_namespaced_persistent_volume_claim(field_selector=field_selector,
                                                               namespace=experiment.namespace)

        if not response.items:
            pvc_size = self._context.default_pvc_size or self.DEFAULT_PVC_SIZE

            # create PVC for NFS server
            resource_req = client.V1ResourceRequirements(requests={'storage': pvc_size + 'i'})
            pvc_spec = client.V1PersistentVolumeClaimSpec(access_modes=['ReadWriteOnce'], resources=resource_req)
            pvc = client.V1PersistentVolumeClaim(metadata=client.V1ObjectMeta(name=self.DEFAULT_NFS_PVC_NAME),
                                                 spec=pvc_spec)
            api.create_namespaced_persistent_volume_claim(namespace=experiment.namespace, body=pvc)

            # create NFS server
            nfs_pod_container = client.V1Container(name='nfs-server', image='k8s.gcr.io/volume-nfs:0.8',
                                                   ports=[client.V1ContainerPort(name='nfs', container_port=2049),
                                                          client.V1ContainerPort(name='mountd', container_port=20048),
                                                          client.V1ContainerPort(name='rpcbind', container_port=111)],
                                                   security_context=client.V1SecurityContext(privileged=True),
                                                   volume_mounts=[client.V1VolumeMount(mount_path='/exports',
                                                                                       name='nfs-server-volume')])
            nfs_pod_volume_source = client.V1PersistentVolumeClaimVolumeSource(claim_name=self.DEFAULT_NFS_PVC_NAME)
            nfs_pod_volume = client.V1Volume(name='nfs-server-volume', persistent_volume_claim=nfs_pod_volume_source)
            nfs_pod_spec = client.V1PodSpec(containers=[nfs_pod_container], volumes=[nfs_pod_volume])
            nfs_pod = client.V1Pod(metadata=client.V1ObjectMeta(name='nfs-server', labels={'role': 'nfs-server'}),
                                   spec=nfs_pod_spec)
            api.create_namespaced_pod(namespace=experiment.namespace, body=nfs_pod)

            nfs_service_spec = client.V1ServiceSpec(ports=[client.V1ServicePort(name='nfs', port=2049),
                                                           client.V1ServicePort(name='mountd', port=20048),
                                                           client.V1ServicePort(name='rpcbind', port=111)],
                                                    selector={'role': 'nfs-server'})
            nfs_service = client.V1Service(metadata=client.V1ObjectMeta(name='nfs-server'), spec=nfs_service_spec)
            service_result = api.create_namespaced_service(namespace=experiment.namespace, body=nfs_service)

            # create NFS PV and PVC
            pv_spec = client.V1PersistentVolumeSpec(capacity={'storage': '1Mi'},
                                                    access_modes=['ReadWriteMany'],
                                                    storage_class_name='nfs',
                                                    persistent_volume_reclaim_policy='Delete',
                                                    nfs=client.V1NFSVolumeSource(server=service_result.spec.cluster_ip,
                                                                                 path='/'))
            pv = client.V1PersistentVolume(metadata=client.V1ObjectMeta(name='pvc-nfs-{}'.format(experiment.namespace)),
                                           spec=pv_spec)
            api.create_persistent_volume(body=pv)

            resource_req = client.V1ResourceRequirements(requests={'storage': '1Mi'})
            pvc_spec = client.V1PersistentVolumeClaimSpec(access_modes=['ReadWriteMany'],
                                                          resources=resource_req,
                                                          storage_class_name="nfs")
            pvc = client.V1PersistentVolumeClaim(metadata=client.V1ObjectMeta(name='nfs'), spec=pvc_spec)
            api.create_namespaced_persistent_volume_claim(namespace=experiment.namespace, body=pvc)


def check_env():
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
