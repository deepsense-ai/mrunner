import argparse
import sys
import os

from datetime import datetime

from mrunner.mrunner_api import MRunnerHelper

from mrunner.mrunner_cli import MRunnerCLI
from mrunner.prometheus import PrometheusBackend
from mrunner.tasks import PlgridTask
from mrunner.utils import id_generator

PLGRID_USERNAME = os.environ.get('PLGRID_USERNAME', 'plghenrykm')
MRUNNER_SCRATCH_SPACE = os.environ.get('MRUNNER_SCRATCH_SPACE', '/net/scratch/people/plghenrykm/pmilos/mrunner')
PLGRID_HOST = os.environ.get('PLGRID_HOST', 'pro.cyfronet.pl')

class MRunnerPLGridCLI(MRunnerCLI):
    def __init__(self, mrunner_api, prometheus_api):
        self.mrunner_api = mrunner_api
        self.prometheus_api = prometheus_api

    def create_parser(self):
        parser = argparse.ArgumentParser(description='',  fromfile_prefix_chars='@')

        parser.add_argument('--storage_url', type=str)
        parser.add_argument('--exp_dir_path', type=str)

        parser.add_argument('--partition', type=str, default='plgrid-testing')
        parser.add_argument('--paths_to_dump', type=str, nargs='+')
        parser.add_argument('--pythonpath', type=str)
        parser.add_argument('--neptune_conf', type=str, default=None)
        parser.add_argument('--tags', default=[], type=str, nargs='+')
        parser.add_argument('--paths_to_dump_conf', type=str)
        parser.add_argument('--name', type=str, default='test')
        parser.add_argument('--project', type=str, default='test')
        parser.add_argument('--config', type=str)
        parser.add_argument('--experiment_id', type=str, default="")
        parser.add_argument('--with_yaml', action='store_true')

        # TODO(maciek): hack for anaconda
        parser.add_argument('--after_module_load_cmd', type=str)
        parser.add_argument('--venv_path', type=str)
        parser.add_argument('--cores', type=int, default=24)
        parser.add_argument('--ntasks', type=int, default=24)
        parser.add_argument('--time', type=str, default='24:00:00')
        parser.add_argument('--neptune', action='store_true')
        parser.add_argument('--srun', action='store_true')
        parser.add_argument('--sbatch', action='store_true')
        return parser



    def main(self, argv):

        self.argv = argv
        mrunner_args, rest_argv = self.parse_argv()


        if mrunner_args.storage_url is not None:
            # INFO(maciek): random noise added is for purpose!
            exp_dir_path = os.path.join(mrunner_args.storage_url, datetime.now().strftime('%Y_%m_%d_%H_%M_%S') + '_' + id_generator(4))
            print('exp_dir_path', exp_dir_path)
        else:
            print('Warning! no exp_dir_path set')
            exp_dir_path = '.'
        if int(mrunner_args.srun) + int(mrunner_args.sbatch) != 1:
            raise RuntimeError('Please provide exactly one of --srun, --sbatch')

        resource_dir_path = os.path.join(exp_dir_path, 'src')

        paths_to_dump = self._parse_paths_to_dump(resource_dir_path,
                                                  mrunner_args.paths_to_dump_conf,
                                                  mrunner_args.paths_to_dump)
        print(paths_to_dump)

        remote_config_path = os.path.join(resource_dir_path, 'config.yaml')

        if mrunner_args.neptune:
            if mrunner_args.config is None:
                raise RuntimeError('Please supply --config!')
            self.prometheus_api.mkdir(resource_dir_path)
            self.prometheus_api.copy_paths_rel(paths_to_dump, resource_dir_path)
            new_local_config_path = self.mrunner_api.config_to_yaml(mrunner_args.config,
                                                                    mrunner_args.name,
                                                                    mrunner_args.project)


            self.prometheus_api.copy_path(remote_config_path, new_local_config_path)

            paths_to_dump_for_neptune = [os.path.join(p['dst'], os.path.basename(p['src'])) for p in paths_to_dump]
            print(paths_to_dump_for_neptune)
            local_task = self.mrunner_api.create_neptune_run_command(config_path=remote_config_path,
                                                                     paths_to_dump=paths_to_dump_for_neptune,
                                                                     storage_url=mrunner_args.storage_url,
                                                                     tags=mrunner_args.tags,
                                                                     neptune_conf_path=mrunner_args.neptune_conf,
                                                                     rest_argv=rest_argv)
            command_list = local_task.command

            if mrunner_args.neptune_conf is not None:
                with open(mrunner_args.neptune_conf) as f:
                    for line in f.readlines():
                        command_list = [line] + command_list

            command = ' '.join(command_list)
            print(command)

            env = local_task.env
            env['EXPERIMENT_ID'] = mrunner_args.experiment_id
            env['STORAGE_URL'] = mrunner_args.storage_url
            env['RESOURCE_DIR_PATH'] = resource_dir_path

            if mrunner_args.pythonpath:
                env['PYTHONPATH'] = mrunner_args.pythonpath

            log_path = '/dev/null'
            task = PlgridTask(command=command, cwd=resource_dir_path, env=env, venv_path=mrunner_args.venv_path,
                              after_module_load_cmd=mrunner_args.after_module_load_cmd)

        else:
            self.prometheus_api.mkdir(resource_dir_path)
            self.prometheus_api.copy_paths_rel(paths_to_dump, resource_dir_path)
            parms_argv = rest_argv
            if mrunner_args.with_yaml:
                parms_argv.append(" --yaml {}".format(remote_config_path))
                new_local_config_path = self.mrunner_api.config_to_yaml(mrunner_args.config,
                                                                        mrunner_args.name,
                                                                        mrunner_args.project)

                self.prometheus_api.copy_path(remote_config_path, new_local_config_path)

            print("XXXXXXXXXXXXXX:{}".format(parms_argv))


            local_task = self.mrunner_api.create_normal_run_command(rest_argv, exp_dir_path=exp_dir_path)
            command = ' '.join(local_task.command)
            env = local_task.env
            env['EXPERIMENT_ID'] = mrunner_args.experiment_id
            env['STORAGE_URL'] = mrunner_args.storage_url
            env['RESOURCE_DIR_PATH'] = resource_dir_path

            if mrunner_args.pythonpath:
                env['PYTHONPATH'] = "$PYTHONPATH:{}".format(mrunner_args.pythonpath)

            log_path = os.path.join(resource_dir_path, "job_logs.txt")
            task = PlgridTask(command=command, cwd=resource_dir_path, env=env, venv_path=mrunner_args.venv_path,
                              after_module_load_cmd=mrunner_args.after_module_load_cmd, )


        if mrunner_args.srun:
            self.prometheus_api.srun(task, partition=mrunner_args.partition,
                                     cores=mrunner_args.cores, ntasks=mrunner_args.ntasks)
        elif mrunner_args.sbatch:
            self.prometheus_api.sbatch(task, partition=mrunner_args.partition,
                                       cores=mrunner_args.cores,
                                       time=mrunner_args.time,
                                       stdout_path = log_path,
                                       ntasks=mrunner_args.ntasks)



def main():
    prometheus = PrometheusBackend(username=PLGRID_USERNAME, host=PLGRID_HOST, scratch_space=MRUNNER_SCRATCH_SPACE)
    mrunner_api = MRunnerHelper()
    mrunner_cli = MRunnerPLGridCLI(mrunner_api, prometheus)
    sys.exit(mrunner_cli.main(sys.argv))


if __name__ == '__main__':
    main()



