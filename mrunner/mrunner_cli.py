import argparse

import sys

import os

from datetime import datetime

from mrunner.mrunner_api import MRunnerHelper

class MRunnerCLI(object):
    def parse_argv(self):
        parser = self.create_parser()
        divider_pos = self.argv.index('--')
        mrunner_argv = self.argv[1:divider_pos]
        rest_argv = self.argv[divider_pos + 1:]

        mrunner_args = parser.parse_args(args=mrunner_argv)
        return mrunner_args, rest_argv

    def _parse_paths_to_dump(self, resource_dir_path, paths_to_dump_conf, paths_to_dump):
        # TODO(maciek): This is broken :P
        res_paths_to_dump = []

        if paths_to_dump_conf is not None:
            with open(paths_to_dump_conf) as f:
                for line in f.readlines():
                    src, dst_rel = line.split(' ')
                    dst = os.path.join(resource_dir_path, dst_rel)
                    res_paths_to_dump.append({'src': src, 'dst': dst, 'dst_rel': dst_rel})
        else:
            # INFO(maciek): it seems when we pass args from file the list is treated as one arg?

            for maybe_path_to_dump in paths_to_dump:
                print('maybe', maybe_path_to_dump)
                for path_to_dump in maybe_path_to_dump.split(' '):
                    if len(path_to_dump) == 0:
                        continue
                    print('path_to_dump', path_to_dump, len(path_to_dump))
                    #dst_rel = path_to_dump
                    dst_rel = '.'
                    src = os.path.abspath(path_to_dump)
                    dst = os.path.join(resource_dir_path, dst_rel)
                    # TODO(maciek): I do not understand the semantics here, src, dst, dst_rel???
                    res_paths_to_dump.append({'src': src, 'dst': dst, 'dst_rel': dst_rel})

        return res_paths_to_dump


class MRunnerLocalCLI(MRunnerCLI):
    def __init__(self, mrunner_api):
        self.mrunner_api = mrunner_api

    def create_parser(self):
        parser = argparse.ArgumentParser(description='', fromfile_prefix_chars='@')
        parser.add_argument('--storage_url', type=str)
        parser.add_argument('--exp_dir_path', type=str)

        parser.add_argument('--paths_to_dump', type=str, nargs='+')
        parser.add_argument('--pythonpath', type=str)
        parser.add_argument('--neptune_conf_path', type=str, default=None)

        parser.add_argument('--tags', default=[], type=str, nargs='+')

        parser.add_argument('--paths_to_dump_conf', type=str)

        parser.add_argument('--name', type=str, default='test')
        parser.add_argument('--project', type=str, default='test')

        parser.add_argument('--neptune_host', type=str)
        parser.add_argument('--neptune_port', type=str)
        parser.add_argument('--neptune_username', type=str)
        parser.add_argument('--neptune_password', type=str)


        parser.add_argument('--docker_image', type=str)
        parser.add_argument('--docker_bin', type=str, default='docker')
        parser.add_argument('--neptune', action='store_true')
        parser.add_argument('--config', type=str)
        return parser

    def main(self, argv):
        # def handler(signum, frame):
        #     print 'Signal handler called with signal', signum
        #
        # signal.signal(signal.SIGTERM, handler)
        # signal.signal(signal.SIGINT, handler)
        self.argv = argv
        mrunner_args, rest_argv = self.parse_argv()


        if mrunner_args.storage_url is not None:
            exp_dir_path = os.path.join(mrunner_args.storage_url, datetime.now().strftime('%Y_%m_%d_%H_%M_%S'))
            print('exp_dir_path', exp_dir_path)
        else:
            print('Warning! no exp_dir_path set')
            exp_dir_path = '.'

        resource_dir_path = os.path.join(exp_dir_path, 'src')

        if mrunner_args.neptune:
            if mrunner_args.config is None:
                raise RuntimeError('Please supply --config!')
            # paths_to_dump = self._parse_paths_to_dump(resource_dir_path,
            #                                       mrunner_args.paths_to_dump_conf,
            #                                       mrunner_args.paths_to_dump)


            new_local_config_path = self.mrunner_api.config_to_yaml(mrunner_args.config,
                                                                    mrunner_args.name,
                                                                    mrunner_args.project)

            local_task = self.mrunner_api.create_neptune_run_command(config_path=new_local_config_path,
                                                                     paths_to_dump=mrunner_args.paths_to_dump,
                                                                     storage_url=mrunner_args.storage_url,
                                                                     neptune_conf_path=mrunner_args.neptune_conf_path,
                                                                     tags=mrunner_args.tags,
                                                                     neptune_host=mrunner_args.neptune_host,
                neptune_port=mrunner_args.neptune_port,
                neptune_username=mrunner_args.neptune_username,
                neptune_password=mrunner_args.neptune_password,
                                                                     rest_argv=rest_argv,
                                                                     docker_image=mrunner_args.docker_image)
            if mrunner_args.pythonpath:
                local_task.env['PYTHONPATH'] = mrunner_args.pythonpath

            self.mrunner_api.run_task_local(local_task)
        else:
            if mrunner_args.docker_image is not None:
                raise NotImplementedError
                #return self.mrunner_api.handle_docker_no_neptune(mrunner_args, rest_argv)

            local_task = self.mrunner_api.create_normal_run_command(rest_argv, exp_dir_path=exp_dir_path)

            if mrunner_args.pythonpath:
                local_task.env['PYTHONPATH'] = mrunner_args.pythonpath
            self.mrunner_api.run_task_local(local_task)


def main():
    mrunner_api = MRunnerHelper()
    mrunner_cli = MRunnerLocalCLI(mrunner_api)
    sys.exit(mrunner_cli.main(sys.argv))

if __name__ == '__main__':
    main()



