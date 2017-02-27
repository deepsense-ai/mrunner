#!/usr/bin/env python
import argparse
import os
import random
import string

import sys

import subprocess
import yaml
from datetime import datetime

import errno

def parser_to_yaml(config_path):
    import imp
    config_module = imp.load_source('create_parser', config_path)
    p = NeptuneDummyParser()
    yaml_str = config_module.create_parser(p).gen_yaml()
    return yaml_str



def create_parser():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--storage_url', type=str)
    parser.add_argument('--exp_dir_path', type=str)

    parser.add_argument('--paths_to_dump', type=str, nargs='+')

    parser.add_argument('--tags', default=None, type=str, nargs='+')

    parser.add_argument('--paths_to_dump_conf', type=str)

    parser.add_argument('--docker_img', type=str)
    parser.add_argument('--docker_bin', type=str, default='docker')
    parser.add_argument('--neptune', action='store_true')
    parser.add_argument('--config', type=str)
    return parser

def mkdir_p(path):
    try:
        os.makedirs(path)
        return path
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            return path
        else:
            raise


def id_generator(n=10):
   return ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(n))


class NeptuneDummyParser(argparse.ArgumentParser):
    def __init__(self):
        pass
        self.parameters = []


    def add_argument(self, *args, **kwargs):
        print args, kwargs
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
                                'description': '',
                                'required': False
                                }
        if default is not None:
            d['default'] = default

        self.parameters.append(d)
    def gen_yaml(self):
        res = {'name': 'test',
               'description': 'test',
               'project': 'test',
               'parameters': self.parameters
        }
        return yaml.dump(res)

class MRunner(object):
    def __init__(self, argv):
        self.argv = argv

    def parser_argv(self):
        parser = create_parser()
        divider_pos = self.argv.index('--')
        self.mrunner_argv = self.argv[1:divider_pos]
        self.rest_argv = self.argv[divider_pos + 1:]

        self.mrunner_args = parser.parse_args(args=self.mrunner_argv)
        print self.mrunner_args
        print self.mrunner_argv
        print self.rest_argv


    def handle_docker_no_neptune(self):
        t = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
        exp_dir_path = os.path.join(self.mrunner_args.storage_url, t, 'exp_dir')
        resource_dir_path = os.path.join(self.mrunner_args.storage_url, t, 'res_dir')
        mkdir_p(exp_dir_path)
        mkdir_p(resource_dir_path)

        docker_img = self.mrunner_args.docker_img
        docker_bin = self.mrunner_args.docker_bin
        paths_to_dump_conf = self.mrunner_args.paths_to_dump_conf
        with open(paths_to_dump_conf) as f:
            for line in f.readlines():
                src, dst_rel = line.split(' ')
                dst = os.path.join(resource_dir_path, dst_rel)
                print dst_rel
                print src, dst
                cmd = 'cp -r {src} {dst}'.format(src=src, dst=dst)
                print cmd
                os.system(cmd)

        with open(os.path.join(exp_dir_path, 'cmd.txt'), 'w') as f:
            print >> f, ' '.join(sys.argv)


        command = '{docker_bin} run -i -t -e LOCAL_USER_ID=`id -u $USER`  -v {resource_dir_path}:/wdir/res_dir -v {exp_dir_path}:/wdir/exp_dir --workdir /wdir/res_dir {docker_img} '.format(
            docker_bin=docker_bin,
                                                                                            docker_img=docker_img,
                                                                                            exp_dir_path=exp_dir_path,
                                                                                            resource_dir_path=resource_dir_path)
        command = filter(lambda a: len(a) > 0, command.split(' '))
        rest_cmd = ' '.join(self.rest_argv)
        rest_cmd = ['/bin/bash', '-c', "'{rest_cmd}'".format(rest_cmd=rest_cmd)]
        command += rest_cmd
        print 'COMMAND'
        print command
        self.wait_for_command(command)

    def handle_normal_run(self, exp_dir_path):
        env = {'MRUNNER_EXP_DIR_PATH': exp_dir_path, 'MRUNNER_UNDER_NEPTUNE': '0'}
        command = self.rest_argv
        print('Will run command:', command)
        self.wait_for_command(command, env)
        print('exp_dir_path', exp_dir_path)
        return 0

    def handle_neptune_run(self, exp_dir_path):
        paths_to_dump = self.mrunner_args.paths_to_dump
        print 'kurwa neptune'

        main_path = self.rest_argv[0]
        if main_path == 'python':
            main_path = self.rest_argv[1]
            self.rest_argv = self.rest_argv[1:]

        mrunner_args = self.mrunner_args

        config_path = None

        if mrunner_args.config is None:
            raise RuntimeError('Please supply --config!')

        if mrunner_args.config is not None:
            if mrunner_args.config[-2:] == 'py':
                yaml_str = parser_to_yaml(mrunner_args.config)
                path = '/tmp/mrunner_config_{id}.yaml'.format(id=id_generator(20))
                f = open(path, 'w')
                print >> f, yaml_str
                f.close()
                print yaml_str
                config_path = path
            elif mrunner_args.config[-4:] == 'yaml':
                config_path = mrunner_args.config
            else:
                raise RuntimeError()

        neptune_command = ['neptune', 'run', main_path, '--config', config_path, '--storage-url', mrunner_args.storage_url]

        if paths_to_dump is not None:
            neptune_command += ['--paths-to-dump'] + paths_to_dump

        command = neptune_command + ['--'] + self.rest_argv[1:]
        print('command', command)

        env = {'MRUNNER_EXP_DIR_PATH': exp_dir_path, 'MRUNNER_UNDER_NEPTUNE': '1'}

        self.wait_for_command(command, env)
        print exp_dir_path
        return 0

    def wait_for_command(self, command, env_dict):
        print ' '.join(command)
        child_env = os.environ.copy()
        child_env.update(env_dict)
        print command

        #print('env_dict', env_dict)
        #print('env', child_env)
        try:
            proc = subprocess.Popen(' '.join(command), shell=True, env=child_env)
            proc.wait()
        except KeyboardInterrupt:
            print 'Interrupted by user!'

    def main(self):

        # def handler(signum, frame):
        #     print 'Signal handler called with signal', signum
        #
        # signal.signal(signal.SIGTERM, handler)
        # signal.signal(signal.SIGINT, handler)

        self.parser_argv()
        exp_dir_path = None

        if self.mrunner_args.tags is not None:
            raise NotImplementedError

        if self.mrunner_args.storage_url is not None:
            exp_dir_path = os.path.join(self.mrunner_args.storage_url, datetime.now().strftime('%Y_%m_%d_%H_%M_%S'))
            print('exp_dir_path', exp_dir_path)
        else:
            print('Warning! no exp_dir_path set')
            exp_dir_path = '.'

        if self.mrunner_args.docker_img is not None:
            return self.handle_docker_no_neptune()

        if self.mrunner_args.neptune:
            return self.handle_neptune_run(exp_dir_path)
        else:
            return self.handle_normal_run(exp_dir_path)


def main():
    mrunner = MRunner(sys.argv)
    sys.exit(mrunner.main())

if __name__ == '__main__':
    main()


