import argparse
import shutil
import sys

import datetime
import os

from os.path import isfile

from mrunner.kubernetes_backend import KubernetesBackend, KubeVolumeMount
from mrunner.mrunner_api import MRunnerHelper
from mrunner.mrunner_cli import MRunnerCLI
from mrunner.utils import mkdir_p, id_generator

DUMP_SUBDIRECTORY_NAME = 'dump'
class MRunnerKuberntesCLI(MRunnerCLI):
    def __init__(self, mrunner_helper, kubernetes_backend):
        self.mrunner_helper = mrunner_helper
        self.kubernetes_backend = kubernetes_backend

    def create_parser(self):
        parser = argparse.ArgumentParser(description='',  fromfile_prefix_chars='@')
        parser.add_argument('--storage_url', type=str, required=True)
        parser.add_argument('--paths_to_dump', type=str, nargs='+', default=[])
        parser.add_argument('--name', type=str, default='test')
        parser.add_argument('--project', type=str, default='test')


        parser.add_argument('--tags', default=[], type=str, nargs='+')
#        parser.add_argument('--paths_to_dump_conf', type=str)
        parser.add_argument('--nr_gpus', type=int, default=1)

        #parser.add_argument('--venv_path', type=str, default='/net/people/plghenrykm/maciek/venvs/tpack')
        parser.add_argument('--docker_image', type=str, required=True)

        parser.add_argument('--pythonpath', type=str)
        parser.add_argument('--node_selector_key', type=str)
        parser.add_argument('--node_selector_value', type=str)

        parser.add_argument('--interactive', action='store_true')

        parser.add_argument('--neptune', action='store_true')
        parser.add_argument('--neptune_exp_config', type=str)

        parser.add_argument('--neptune_host', type=str)
        parser.add_argument('--neptune_port', type=str)
        parser.add_argument('--neptune_username', type=str)
        parser.add_argument('--neptune_password', type=str)

        parser.add_argument('--dry_run', action='store_true')
        return parser



    def main(self, argv):
        self.argv = argv
        mrunner_args, rest_argv = self.parse_argv()

        # INFO(maciek): This is a directory where we now copy needed files, but then
        # we will run 'neptune run', and it itself will create new exp_dir
        # This is fucked!

        subdir = datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S') + '_' + id_generator(4)
        temp_exp_dir_path = os.path.join(mrunner_args.storage_url, subdir)
        print('temp_exp_dir_path', temp_exp_dir_path)
        dump_dir = os.path.join(temp_exp_dir_path, DUMP_SUBDIRECTORY_NAME)
        paths_to_dump = self._parse_paths_to_dump(dump_dir,
                                                    None,
                                                  mrunner_args.paths_to_dump)
        mkdir_p(dump_dir)
        self.copy_paths(paths_to_dump)
        if mrunner_args.neptune:
            tmp_config_path = self.mrunner_helper.config_to_yaml(mrunner_args.neptune_exp_config,
                                                                mrunner_args.name,
                                                                mrunner_args.project)

            config_path = os.path.join(dump_dir, 'config.yaml')
            self.copy_path(config_path, tmp_config_path)
            print('config_path', config_path)
            paths_to_dump_for_neptune = [p['dst']  for p in paths_to_dump]

            # We will be constructing neptune run command here
            command_with_env = self.mrunner_helper.create_neptune_run_command(
                config_path=config_path,
                paths_to_dump=paths_to_dump_for_neptune,
                storage_url=mrunner_args.storage_url,
                tags=mrunner_args.tags,
                neptune_host=mrunner_args.neptune_host,
                neptune_port=mrunner_args.neptune_port,
                neptune_username=mrunner_args.neptune_username,
                neptune_password=mrunner_args.neptune_password,
                rest_argv=rest_argv)
        else:
            command_with_env = self.mrunner_helper.create_normal_run_command(rest_argv=rest_argv,
                                                                             exp_dir_path=temp_exp_dir_path)

        print('command_with_env', command_with_env.command, command_with_env.env)
        pod_name = 'mrunner-pod-{id}'.format(id=id_generator(10))

        # TODO(maciek): temporary!!!
        volume_mounts = [
            KubeVolumeMount(name='storage',
                            mountPath='/mnt/mhome',
                            hostPath={'path': '/mnt/mhome'}
                            )
        ]


        # volume_mounts = [
        #     KubeVolumeMount(name='storage',
        #                     mountPath=mrunner_args.storage_url,
        #                     hostPath={'path': mrunner_args.storage_url}
        #                     )
        # ]

        if mrunner_args.dry_run is True:
            print('only dry-run, not executing!!!')
        else:
            # INFO(maciek): kube's semantics is not obvious at all what args, and command mean
            # https://kubernetes.io/docs/tasks/inject-data-application/define-command-argument-container/#define-a-command-and-arguments-when-you-create-a-pod
            # see the table that comparse Docker and Kube

            # INFO(maciek): this will use container's default entrypoint
            args = command_with_env.command
            command = None
            env = {}
            env.update(command_with_env.env)
            if mrunner_args.pythonpath is not None:
                env['PYTHONPATH'] = mrunner_args.pythonpath

            print('Pod env will be {}'.format(env))


            self.kubernetes_backend.run_command_in_pod(pod_name=pod_name,
                                                       image=mrunner_args.docker_image,
                                                       nr_gpus=mrunner_args.nr_gpus,
                                                       args=args,
                                                       command=command,
                                                       volume_mounts=volume_mounts,
                                                       interactive=mrunner_args.interactive,
                                                       workingDir=dump_dir,
                                                       node_selector_key=mrunner_args.node_selector_key,
                                                       node_selector_value=mrunner_args.node_selector_value,
                                                       env=env,
                                                       )

    def copy_paths(self, paths_to_dump):
        for d in paths_to_dump:
            dst_path, src_path = d['dst'], d['src']
            self.copy_path(dst_path=dst_path, src_path=src_path)

    def copy_path(self, dst_path, src_path):
        print('copy_path dst = {}, src = {}'.format(dst_path, src_path))
        if isfile(src_path):
            shutil.copy(src=src_path, dst=dst_path)
        else:
            shutil.copytree(src_path, dst_path)


KUBE_CONFIG_PATH = '~/.kube/config'


def main():
    kubernetes_backend = KubernetesBackend()
    mrunner_helper = MRunnerHelper()
    cli = MRunnerKuberntesCLI(mrunner_helper, kubernetes_backend)
    return cli.main(sys.argv)

if __name__ == '__main__':
    sys.exit(main())



