#!/usr/bin/env python
from __future__ import print_function
import argparse
import os
import subprocess
import sys
from datetime import datetime

import yaml

from mrunner.tasks import LocalTask
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


class MRunner(object):
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

    def create_normal_run_command(self, rest_argv, exp_dir_path):
        env = {'MRUNNER_EXP_DIR_PATH': exp_dir_path, 'MRUNNER_UNDER_NEPTUNE': '0'}
        command = rest_argv
        return LocalTask(command=command, env=env)

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


    def create_neptune_run_command(self, config_path, paths_to_dump, storage_url, rest_argv, tags=[], neptune_conf_path=None):
        print('create_neptune', config_path)
        print(paths_to_dump)
        print(storage_url)
        print(rest_argv)
        main_path = rest_argv[0]
        if main_path == 'python':
            main_path = rest_argv[1]
            rest_argv = rest_argv[1:]

        neptune_command = ['neptune', 'run', main_path, '--config', config_path, '--storage', storage_url]
        if tags:
            neptune_command += ['--tags'] + tags

        if paths_to_dump is not None:
            neptune_command += ['--paths-to-copy'] + paths_to_dump


        command = neptune_command + ['--'] + rest_argv[1:]

        if neptune_conf_path is not None:
            with open(neptune_conf_path) as f:
                for line in f.readlines():
                    command = [line] + command

        env = {
               'MRUNNER_UNDER_NEPTUNE': '1'
        }
        return LocalTask(command=command, env=env)

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





