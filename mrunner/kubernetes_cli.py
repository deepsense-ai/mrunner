#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import shutil
import sys
from os.path import isfile

from mrunner.cmd import NeptuneWrapperCmd, Cmd
from mrunner.kubernetes import KubeVolumeMount, KubernetesBackend
from mrunner.prometheus import parse_paths_to_dump
from mrunner.utils import mkdir_p, id_generator, get_experiment_dirname, parse_argv

DUMP_SUBDIRECTORY_NAME = 'dump'


def run(mrunner_args, rest_argv):
    k8s_backend = KubernetesBackend()

    # INFO(maciek): This is a directory where we now copy needed files, but then
    # we will run 'neptune run', and it itself will create new exp_dir
    # This is fucked!
    temp_exp_dir_path = os.path.join(mrunner_args.storage_url, get_experiment_dirname())
    print('temp_exp_dir_path', temp_exp_dir_path)
    dump_dir = os.path.join(temp_exp_dir_path, DUMP_SUBDIRECTORY_NAME)
    paths_to_dump = parse_paths_to_dump(dump_dir, None, mrunner_args.paths_to_dump)

    mkdir_p(dump_dir)
    copy_paths(paths_to_dump)
    if mrunner_args.neptune:
        config_path = os.path.join(dump_dir, 'config.yaml')
        copy_path(config_path, mrunner_args.neptune_exp_config)
        print('config_path', config_path)
        paths_to_dump_for_neptune = [p['dst'] for p in paths_to_dump]

        cmd = NeptuneWrapperCmd(cmd=rest_argv, experiment_config_path=config_path,
                                neptune_storage=mrunner_args.storage_url,
                                paths_to_dump=paths_to_dump_for_neptune,
                                additional_tags=mrunner_args.tags)
    else:
        cmd = Cmd(cmd=rest_argv, exp_dir_path=temp_exp_dir_path)

    print('command_with_env', cmd.command, cmd.env)
    pod_name = 'mrunner-pod-{id}'.format(id=id_generator(10))

    # TODO(maciek): temporary!!!
    volume_mounts = [
        KubeVolumeMount(name='storage',
                        mountPath='/mnt/ml-team/rl/kubernetes_storage',
                        hostPath={'path': '/mnt/ml-team/rl/kubernetes_storage'}
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
        args = cmd.command
        command = None
        env = {}
        env.update(cmd.env)
        if mrunner_args.pythonpath is not None:
            env['PYTHONPATH'] = mrunner_args.pythonpath

        print('Pod env will be {}'.format(env))

        k8s_backend.run_command_in_pod(pod_name=pod_name,
                                       image=mrunner_args.docker_image,
                                       nr_gpus=mrunner_args.nr_gpus,
                                       args=args,
                                       command=command,
                                       volume_mounts=volume_mounts,
                                       interactive=mrunner_args.interactive,
                                       workingDir=dump_dir,
                                       node_selector_key=mrunner_args.node_selector_key,
                                       node_selector_value=mrunner_args.node_selector_value,
                                       env=env)


def copy_paths(paths_to_dump):
    for d in paths_to_dump:
        dst_path, src_path = d['dst'], d['src']
        copy_path(dst_path=dst_path, src_path=src_path)


def copy_path(dst_path, src_path):
    print('copy_path dst = {}, src = {}'.format(dst_path, src_path))
    if isfile(src_path):
        shutil.copy(src=src_path, dst=dst_path)
    else:
        os.system('cp -r {src} {dst}'.format(src=src_path, dst=dst_path))


def main():
    parser = argparse.ArgumentParser(description='', fromfile_prefix_chars='@')
    parser.add_argument('--storage_url', type=str, required=True)

    parser.add_argument('--paths_to_dump', type=str, nargs='+', default=[])
    parser.add_argument('--tags', default=[], type=str, nargs='+')

    parser.add_argument('--nr_gpus', type=int, default=1)
    parser.add_argument('--docker_image', type=str, required=True)

    parser.add_argument('--pythonpath', type=str)
    parser.add_argument('--node_selector_key', type=str)
    parser.add_argument('--node_selector_value', type=str)

    parser.add_argument('--interactive', action='store_true')

    parser.add_argument('--neptune', action='store_true')
    parser.add_argument('--neptune_exp_config', type=str)

    parser.add_argument('--dry_run', action='store_true')

    mrunner_args, rest_argv = parse_argv(parser, sys.argv)
    sys.exit(run(mrunner_args, rest_argv))


if __name__ == '__main__':
    main()
