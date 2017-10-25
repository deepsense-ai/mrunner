#!/usr/bin/env python
from __future__ import print_function
import argparse
import os
import subprocess
import sys
from datetime import datetime

import yaml

from mrunner.tasks import CommandWithEnv
from mrunner.utils import mkdir_p, id_generator


class NeptuneDummyParser(argparse.ArgumentParser):
    def __init__(self):
        pass
        self.parameters = []


    def add_argument(self, *args, **kwargs):
        print(args, kwargs)
        if len(args) != 1:

            raise RuntimeError()

        name = args[0]
        type = kwargs.get('type', str)
        default = kwargs.get('default', None)
        assert(name[:2] == '--')

        def map_type(t):
            for a, b in [(int, 'int'), (str, 'string'), (float, 'double')]:
                if t == a:
                    return b
            raise RuntimeError()

        d = {'name': name[2:],
                                'type': map_type(type),
                                'description': 'empty description',
                                'required': False
                                }
        if default is not None:
            d['default'] = default

        self.parameters.append(d)

    def gen_yaml(self, name='test', description='empty description', project='test'):
        res = {'name': name,
               'description': description,
               'project': project,
               'parameters': self.parameters
        }
        return yaml.dump(res)


class MRunnerHelper(object):
    def parser_to_yaml(self, config_path, name, project):
        import imp
        config_module = imp.load_source('create_parser', config_path)
        p = NeptuneDummyParser()
        yaml_str = config_module.create_parser(p).gen_yaml(name=name, project=project)
        return yaml_str

    def handle_docker_no_neptune(self, mrunner_args, rest_argv):
        raise NotImplementedError
        t = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
        exp_dir_path = os.path.join(mrunner_args.storage_url, t, 'exp_dir')
        resource_dir_path = os.path.join(mrunner_args.storage_url, t, 'res_dir')
        mkdir_p(exp_dir_path)
        mkdir_p(resource_dir_path)

        docker_img = mrunner_args.docker_img
        docker_bin = mrunner_args.docker_bin
        paths_to_dump_conf = mrunner_args.paths_to_dump_conf
        with open(paths_to_dump_conf) as f:
            for line in f.readlines():
                src, dst_rel = line.split(' ')
                dst = os.path.join(resource_dir_path, dst_rel)
                print(dst_rel)
                print(src, dst)
                cmd = 'cp -r {src} {dst}'.format(src=src, dst=dst)
                print(cmd)
                os.system(cmd)

        with open(os.path.join(exp_dir_path, 'cmd.txt'), 'w') as f:
            print((' '.join(sys.argv)), file=f)


        command = '{docker_bin} run -i -t -e LOCAL_USER_ID=`id -u $USER`  -v {resource_dir_path}:/wdir/res_dir -v {exp_dir_path}:/wdir/exp_dir --workdir /wdir/res_dir {docker_img} '.format(
            docker_bin=docker_bin,
                                                                                            docker_img=docker_img,
                                                                                            exp_dir_path=exp_dir_path,
                                                                                            resource_dir_path=resource_dir_path)
        command = filter(lambda a: len(a) > 0, command.split(' '))
        rest_cmd = ' '.join(rest_argv)
        rest_cmd = ['/bin/bash', '-c', "'{rest_cmd}'".format(rest_cmd=rest_cmd)]
        command += rest_cmd
        print('COMMAND')
        print(command)
        self._wait_for_command(command)

    def config_to_yaml(self, config_path, name, project):
        assert config_path is not None
        if config_path[-2:] == 'py':
            yaml_str = self.parser_to_yaml(config_path, name, project)
            path = '/tmp/mrunner_config_{id}.yaml'.format(id=id_generator(20))
            f = open(path, 'w')
            print(yaml_str, file=f)
            f.close()
            print(yaml_str)
            new_config_path = path
        elif config_path[-4:] == 'yaml':
            new_config_path = config_path
        else:
            raise RuntimeError()
        return new_config_path

    def create_normal_run_command(self, rest_argv, exp_dir_path):
        env = {'MRUNNER_EXP_DIR_PATH': exp_dir_path, 'MRUNNER_UNDER_NEPTUNE': '0'}
        command = rest_argv
        return CommandWithEnv(command=command, env=env)

    def create_yaml_run_command(self, config_path, paths_to_dump, storage_url, rest_argv, tags, exp_dir_path):
        env = {'MRUNNER_EXP_DIR_PATH': exp_dir_path, 'MRUNNER_UNDER_NEPTUNE': '0'}
        # main_path = rest_argv[0]
        base_argv = rest_argv+['--config', config_path, '--storage', storage_url]
        if tags:
            tags_argv = ['--tags'] + tags
        else:
            tags_argv = []

        if paths_to_dump is not None:
            paths_to_dump_argv = ['--paths-to-copy'] + paths_to_dump
        else:
            paths_to_dump_argv = []

        neptune_command = base_argv + tags_argv + paths_to_dump_argv
        command = neptune_command + ['--']

        print("PM: command:{}".format(command))

        return CommandWithEnv(command=command, env=env)




    def create_neptune_run_command(self, config_path, paths_to_dump, storage_url, rest_argv, tags=[], neptune_conf_path=None, docker_image=None,
                                   neptune_host=None, neptune_port=None, neptune_username=None, neptune_password=None):
        print('create_neptune {}'.format(config_path))
        print('paths_to_dump {}'.format(paths_to_dump))
        print('storage_url {}'.format(storage_url))
        print('rest_argv {}'.format(rest_argv))
        main_path = rest_argv[0]
        if main_path == 'python':
            main_path = rest_argv[1]
            rest_argv = rest_argv[1:]

        base_argv = ['neptune', 'run', main_path, '--config', config_path, '--storage', storage_url]
        if tags:
            tags_argv = ['--tags'] + tags
        else:
            tags_argv = []

        if paths_to_dump is not None:
            paths_to_dump_argv = ['--paths-to-copy'] + paths_to_dump
        else:
            paths_to_dump_argv = []

        if docker_image is not None:
            print('Will be using docker')
            docker_image_argv = ['--docker-image', docker_image]
        else:
            docker_image_argv = []

        if neptune_conf_path is None:
            assert neptune_host is not None
            assert neptune_port is not None
            assert neptune_username is not None
            assert neptune_password is not None
            neptune_credentials_argv = ['--host', neptune_host, '--port', neptune_port, '--username',
                                        neptune_username, '--password', neptune_password]
        else:
            neptune_credentials_argv = []

        neptune_command = base_argv + tags_argv + paths_to_dump_argv + docker_image_argv + neptune_credentials_argv
        command = neptune_command + ['--'] + rest_argv[1:]

        if neptune_conf_path is not None:
            with open(neptune_conf_path) as f:
                for line in f.readlines():
                    command = [line] + command


        env = {
               'MRUNNER_UNDER_NEPTUNE': '1'
        }
        return CommandWithEnv(command=command, env=env)

    def run_task_local(self, task):
        print('task.command', task.command)
        print(' '.join(task.command))
        print('task.env', task.env)
        child_env = os.environ.copy()
        child_env.update(task.env)

        try:
            proc = subprocess.Popen(' '.join(task.command), shell=True, env=child_env)
            proc.wait()
        except KeyboardInterrupt:
            print('Interrupted by user!')





