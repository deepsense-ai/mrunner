
import io
import json
import pprint
import subprocess
from collections import namedtuple

import yaml

from mrunner.utils import id_generator

pod_template_yaml = '''
kind: Pod
apiVersion: v1
metadata:
  name: gpu-pod2
spec:
  containers:
  - name: gpu-container
    image: gcr.io/tensorflow/tensorflow:latest-gpu
    imagePullPolicy: Always
    resources:
      requests:
        alpha.kubernetes.io/nvidia-gpu: 1
      limits:
        alpha.kubernetes.io/nvidia-gpu: 1
        
    volumeMounts:
    - name: nvidia-driver-384
      mountPath: /usr/local/nvidia
      readOnly: true
    - name: libcuda-so
      mountPath: /usr/lib/x86_64-linux-gnu/libcuda.so
    - name: libcuda-so-1
      mountPath: /usr/lib/x86_64-linux-gnu/libcuda.so.1
    - name: libcuda-so-384
      mountPath: /usr/lib/x86_64-linux-gnu/libcuda.so.384.59
  
  imagePullSecrets:
    - name: regsecret
    
  restartPolicy: Never
  volumes:
  - name: nvidia-driver-384
    hostPath:
      path: /var/lib/nvidia-docker/volumes/nvidia_driver/384.59
  - name: libcuda-so
    hostPath:
      path: /usr/lib/x86_64-linux-gnu/libcuda.so
  - name: libcuda-so-1
    hostPath:
      path: /usr/lib/x86_64-linux-gnu/libcuda.so.1
  - name: libcuda-so-384
    hostPath:
      path: /usr/lib/x86_64-linux-gnu/libcuda.so.384.59
'''

pod_template2_yaml = '''
apiVersion: v1
metadata:
  name: gpu-pod2
spec:
  containers:
  - name: gpu-container
    image: gcr.io/tensorflow/tensorflow:latest-gpu
    imagePullPolicy: Always
    command: ["/bin/bash"]
    args: ["-c", "for i in {1..100}; sleep 1; echo $i; done"]
    resources:
      requests:
        alpha.kubernetes.io/nvidia-gpu: 1
      limits:
        alpha.kubernetes.io/nvidia-gpu: 1
        
  restartPolicy: Never
'''
KubeVolumeMount = namedtuple('KubeVolumeMount', ['mountPath', 'name', 'hostPath'])


class KubernetesBackend(object):
    def __init__(self, kube_config=None):
        self.kube_config = kube_config

    @classmethod
    def generate_pod_dict(cls, pod_name, image, command, args, nr_gpus, env=None):
        pod_dict = yaml.load(pod_template_yaml)
        pod_dict['metadata']['name'] = pod_name
        if command is not None:
            pod_dict['spec']['containers'][0]['command'] = command

        if args is not None:
            pod_dict['spec']['containers'][0]['args'] = args

        pod_dict['spec']['containers'][0]['resources']['limits']['alpha.kubernetes.io/nvidia-gpu'] = nr_gpus
        pod_dict['spec']['containers'][0]['resources']['requests']['alpha.kubernetes.io/nvidia-gpu'] = nr_gpus
        pod_dict['spec']['containers'][0]['image'] = image

        if env is not None:
            pod_dict['spec']['containers'][0]['env'] = []
            for key, value in env.items():
                pod_dict['spec']['containers'][0]['env'].append({
                    'name': key,
                    'value': value
                })

        return pod_dict
        #return yaml.dump(pod_dict)

    @classmethod
    def generate_pod_dict2(cls, pod_name, image, command, args, nr_gpus):
        pod_dict = yaml.load(pod_template2_yaml)
        pod_dict['metadata']['name'] = pod_name
        pod_dict['spec']['containers'][0]['command'] = command
        pod_dict['spec']['containers'][0]['args'] = args
        pod_dict['spec']['containers'][0]['image'] = image
        return pod_dict

    def add_volume_mounts(self, pod_dict, volume_mounts):
        for volume_mount in volume_mounts:
            pod_dict['spec']['containers'][0]['volumeMounts'].append(
                {'mountPath': volume_mount.mountPath, 'name': volume_mount.name}
            )
            pod_dict['spec']['volumes'].append(
                {'hostPath': volume_mount.hostPath, 'name': volume_mount.name}
            )

    def add_working_dir(self, pod_dict, workingDir):
        pod_dict['spec']['containers'][0]['workingDir'] = workingDir

    def add_node_selector(self, pod_dict, label_key, label_value):
        pod_dict['spec']['nodeSelector'] = {}
        pod_dict['spec']['nodeSelector'][label_key] = label_value

    def run_command_in_pod(self, pod_name, image, nr_gpus,
                           args,
                           command,
                           node_selector_key=None, node_selector_value=None, volume_mounts=[], interactive=False, workingDir=None,
                           env=None):
        pod_dict = self.generate_pod_dict(pod_name, image, command=command,
                                          args=args, nr_gpus=nr_gpus, env=env)
        self.add_volume_mounts(pod_dict, volume_mounts)
        if workingDir is not None:
            self.add_working_dir(pod_dict, workingDir)

        if node_selector_key is not None and node_selector_value is not None:
            self.add_node_selector(pod_dict, node_selector_key, node_selector_value)

        if interactive is True:
            raise NotImplementedError
            # json_str = json.dumps(pod_dict)
            # kubectl_run_command = ['kubectl', 'run', pod_name,
            #                         '-i','--tty',
            #                        '--restart=Never',
            #                        '--image={}'.format(image),
            #                        "--overrides='{pod_dict_json}'".format(pod_dict_json=json_str)
            #                        ]
            # pprint.pprint(pod_dict, indent=4)
            # print(kubectl_run_command)
            # print(' '.join(kubectl_run_command))
        else:
            yaml_str = yaml.dump(pod_dict)

            with open('/tmp/final_yaml.yaml', 'w') as f:
                # print(yaml_str, file=f)
                f.write(yaml_str)

            pprint.pprint(pod_dict)
            self.create_pod(yaml_str)
            print('Pod {pod_name} created!'.format(pod_name=pod_name))
            print('To attach you should run:')
            print('kubectl attach {pod_name}'.format(pod_name=pod_name))
            print('To see logs you should run:')
            print('kubectl logs {pod_name}'.format(pod_name=pod_name))
            print('To get shell at pod run:')
            print('kubectl exec -it {pod_name} /bin/bash'.format(pod_name=pod_name))


    def create_pod(self, yaml_str):
        random_path = '/tmp/{}.yaml'.format(id_generator(10))
        with open(random_path, 'w') as f:
            # print(yaml_str, file=f)
            f.write(yaml_str)

        command = ['kubectl', 'create']
        if self.kube_config is not None:
            command += ['--kubeconfig', self.kube_config]
        command += ['-f', random_path]
        print(' '.join(command))
        # subprocess.run(command, check=True)
        subprocess.call(command)



# res = KubernetesApi.generate_yaml(pod_name='test_pod_name',
#               image='test_image',
#               command='/bin/bash',
#               command_args=['-c', 'sleep 10000'],
#               nr_gpus=1)
# print(res)

