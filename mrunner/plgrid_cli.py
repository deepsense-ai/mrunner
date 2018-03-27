#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import os
import random
import sys

from mrunner.cmd import NeptuneWrapperCmd, YamlCmd, PlgridScript
from mrunner.prometheus import parse_paths_to_dump, PrometheusBackend
from mrunner.utils import get_experiment_dirname, parse_argv

PLGRID_USERNAME = os.environ.get('PLGRID_USERNAME', 'plghenrykm')
MRUNNER_SCRATCH_SPACE = os.environ.get('MRUNNER_SCRATCH_SPACE', '/net/scratch/people/plghenrykm/pmilos/mrunner')
PLGRID_HOST = os.environ.get('PLGRID_HOST', 'pro.cyfronet.pl')


def run(mrunner_args, rest_argv):
    prometheus = PrometheusBackend(username=PLGRID_USERNAME, host=PLGRID_HOST, scratch_space=MRUNNER_SCRATCH_SPACE)

    if int(mrunner_args.srun) + int(mrunner_args.sbatch) != 1:
        raise RuntimeError('Please provide exactly one of --srun, --sbatch')
    if int(mrunner_args.neptune) + int(mrunner_args.with_yaml) != 1:
        raise RuntimeError('Please provide exactly one of --neptune, --with_yaml')

    if mrunner_args.storage_url is not None:
        exp_dir_path = os.path.join(mrunner_args.storage_url, get_experiment_dirname())
        print('exp_dir_path', exp_dir_path)
    else:
        exp_dir_path = '.'
        print('Warning! no exp_dir_path set')

    resource_dir_path = os.path.join(exp_dir_path, 'src')
    remote_config_path = os.path.join(resource_dir_path, 'config.yaml')
    paths_to_dump = parse_paths_to_dump(resource_dir_path, mrunner_args.paths_to_dump_conf, mrunner_args.paths_to_dump)
    print(paths_to_dump)

    prometheus.mkdir(resource_dir_path)
    prometheus.copy_paths_rel(paths_to_dump, resource_dir_path)
    prometheus.copy_path(remote_config_path, mrunner_args.config)

    paths_to_dump_for_neptune = [os.path.join(p['dst'], os.path.basename(p['src'])) for p in paths_to_dump]
    print(paths_to_dump_for_neptune)

    if mrunner_args.neptune:
        if mrunner_args.config is None:
            raise RuntimeError('Please supply --config!')

        neptune_cmd = NeptuneWrapperCmd(rest_argv, remote_config_path,
                                        paths_to_dump=paths_to_dump_for_neptune,
                                        neptune_storage=mrunner_args.storage_url,
                                        additional_tags=mrunner_args.tags)

        # [Blazej] workaround for Neptune tag race
        sleep_command = "sleep {0:.4f}".format(random.random() * 5)
        command = sleep_command + " ; " + neptune_cmd.command
        env = neptune_cmd.env.copy()
        log_path = '/dev/null'
    else:
        cmd = YamlCmd(rest_argv, remote_config_path,
                      paths_to_dump=paths_to_dump_for_neptune,
                      neptune_storage=mrunner_args.storage_url,
                      additional_tags=mrunner_args.tags,
                      exp_dir_path=exp_dir_path)

        command, env = cmd.command, cmd.env.copy()
        log_path = os.path.join(resource_dir_path, "job_logs.txt")

    print(command)
    modules_to_load = []
    if mrunner_args.modules_to_load:
        modules_to_load = mrunner_args.modules_to_load.split(":")
        modules_to_load = [x for x in modules_to_load if x]  # remove empty strings
        print("Modules to load:{}".format(modules_to_load))

    env['EXPERIMENT_ID'] = mrunner_args.experiment_id
    env['STORAGE_URL'] = mrunner_args.storage_url
    env['RESOURCE_DIR_PATH'] = resource_dir_path
    if mrunner_args.pythonpath:
        env['PYTHONPATH'] = mrunner_args.pythonpath

    task = PlgridScript(command, cwd=resource_dir_path, env=env, venv_path=mrunner_args.venv_path,
                        after_module_load_cmd=mrunner_args.after_module_load_cmd,
                        script_name=mrunner_args.script_name, modules_to_load=modules_to_load)

    if mrunner_args.srun:
        prometheus.srun(task, partition=mrunner_args.partition,
                        cores=mrunner_args.cores, ntasks=mrunner_args.ntasks,
                        account=mrunner_args.A,
                        gres=mrunner_args.gres)
    elif mrunner_args.sbatch:
        prometheus.sbatch(task, partition=mrunner_args.partition,
                          cores=mrunner_args.cores,
                          time=mrunner_args.time,
                          stdout_path=log_path,
                          ntasks=mrunner_args.ntasks,
                          account=mrunner_args.A,
                          gres=mrunner_args.gres)


def main():
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description='', fromfile_prefix_chars='@')

    parser.add_argument('--storage_url', type=str)

    parser.add_argument('--partition', type=str, default='plgrid-testing')
    parser.add_argument('--pythonpath', type=str)

    parser.add_argument('--neptune', action='store_true')
    parser.add_argument('--config', type=str)
    parser.add_argument('--paths_to_dump_conf', type=str)
    parser.add_argument('--paths_to_dump', type=str, nargs='+')
    parser.add_argument('--tags', default=[], type=str, nargs='+')
    parser.add_argument('--with_yaml', action='store_true')

    parser.add_argument('--experiment_id', type=str, default="")
    parser.add_argument('--after_module_load_cmd', type=str)
    parser.add_argument('--venv_path', type=str)
    parser.add_argument('--cores', type=int, default=24)
    parser.add_argument('--ntasks', type=int, default=24)
    parser.add_argument('--time', type=str, default='24:00:00')
    parser.add_argument('--srun', action='store_true')
    parser.add_argument('--sbatch', action='store_true')
    parser.add_argument('--script_name', type=str, default="mrunner")
    parser.add_argument('--modules_to_load', type=str)
    parser.add_argument('--A', type=str, default=None)
    parser.add_argument('--gres', type=str, default=None)

    mrunner_args, rest_argv = parse_argv(parser, sys.argv)
    sys.exit(run(mrunner_args, rest_argv))


if __name__ == '__main__':
    main()
