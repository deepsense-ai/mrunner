#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import os
import subprocess
import sys

import yaml

from mrunner.cmd import Cmd, NeptuneWrapperCmd
from mrunner.utils import get_experiment_dirname, parse_argv

LOGGER = logging.getLogger(__name__)


def run_task_locally(task, env_update={}):
    env = os.environ.copy()
    env.update(task.env)
    env.update({k: str(v) for k, v in env_update.items() if v})

    LOGGER.info("Running job locally")
    LOGGER.info("cmd: {}".format(task.command))
    LOGGER.info("env: {}".format(yaml.dump(env)))

    try:
        process = subprocess.Popen(task.command, shell=True, env=env)
        return process.wait()
    except KeyboardInterrupt:
        LOGGER.warning("Interrupted with keyboard")
        return 0


def run_without_neptune(mrunner_args, rest_argv):
    exp_dir_path = os.path.join(mrunner_args.storage_url, get_experiment_dirname())
    if mrunner_args.docker_image:
        raise NotImplementedError()
    task = Cmd(rest_argv, exp_dir_path=exp_dir_path)
    return run_task_locally(task, env_update={'PYTHONPATH': mrunner_args.pythonpath})


def run_with_neptune(mrunner_args, rest_argv):
    if mrunner_args.config is None:
        raise ValueError('config is required while running task with neptune')
    if mrunner_args.storage_url is None:
        raise ValueError('storage_url is required while running task with neptune')
    task = NeptuneWrapperCmd(rest_argv, mrunner_args.config,
                             neptune_storage=mrunner_args.storage_url,
                             additional_tags=mrunner_args.tags,
                             paths_to_dump=mrunner_args.paths_to_dump,
                             docker_image=mrunner_args.docker_image)

    return run_task_locally(task, env_update={'PYTHONPATH': mrunner_args.pythonpath})


def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description='Run experiment on local mahine with optional neptune support',
                                     fromfile_prefix_chars='@')
    parser.add_argument('--storage_url', type=str,
                        help="Path to directory where neptune CLI will store data for experiment provenance")

    # TODO: [PZ] think neptune parameter is redundant (may assume that
    parser.add_argument('--neptune', action='store_true', help='Enable neptune for experiment')
    parser.add_argument('--config', type=str, help='Path to experiment neptune config')
    parser.add_argument('--tags', default=[], type=str, nargs='+', help='Additional (to those from experiment neptune config) tags '
                             'which will be added to neptune call')
    parser.add_argument('--docker_image', type=str, help='Docker image name to use while running experiment'
                                                         'with neptune')
    parser.add_argument('--paths_to_dump', type=str, nargs='+',
                        help="List of files or dirs which will be copied by neptune to storage")
    parser.add_argument('--pythonpath', type=str, help='Additional paths to be added to PYTHONPATH')

    mrunner_args, rest_argv = parse_argv(parser, sys.argv)
    run = {True: run_with_neptune, False: run_without_neptune}[mrunner_args.neptune]
    sys.exit(run(mrunner_args, rest_argv))


if __name__ == '__main__':
    main()
