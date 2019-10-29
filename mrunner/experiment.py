# -*- coding: utf-8 -*-
import logging
import random
import re
import warnings

import attr
import six
from path import Path
import cloudpickle

from mrunner.utils.namesgenerator import id_generator, get_random_name, get_unique_name

LOGGER = logging.getLogger(__name__)

COMMON_EXPERIMENT_MANDATORY_FIELDS = [
    ('backend_type', dict()),
    ('name', dict()),
    ('storage_dir', dict()),
    ('cmd', dict())
]

COMMON_EXPERIMENT_OPTIONAL_FIELDS = [
    ('project', dict(default='sandbox')),
    ('random_name', dict(factory=get_random_name)),
    ('unique_name', dict(default=attr.Factory(get_unique_name, takes_self=True))),
    ('requirements', dict(default=attr.Factory(list), type=list)),
    ('exclude', dict(default=None, type=list)),
    ('paths_to_copy', dict(default=attr.Factory(list), type=list)),
    ('env', dict(default=attr.Factory(dict), type=dict)),
    ('cpu', dict(default=attr.Factory(dict), type=dict)),
    ('mem', dict(default=attr.Factory(dict), type=dict)),
    ('gpu', dict(default=attr.Factory(dict), type=dict)),
    ('cwd', dict(default=attr.Factory(Path.getcwd))),
]

@attr.s
class Experiment(object):

    project = attr.ib()
    name = attr.ib()
    script = attr.ib()
    parameters = attr.ib()
    env = attr.ib(factory=dict)
    paths_to_copy = attr.ib(factory=list)
    tags = attr.ib(factory=list)
    exclude = attr.ib(factory=list)
    random_name = attr.ib(factory=get_random_name)
    unique_name = attr.ib(default=attr.Factory(get_unique_name, takes_self=True))
    git_info = attr.ib(default=None)

    def to_dict(self):
        return attr.asdict(self)


def _merge_experiment_parameters(cli_kwargs, context):
    config = context.copy()
    for k, v in cli_kwargs.items():
        if k not in config:
            LOGGER.debug('New config["{}"]: {}'.format(k, v))
            config[k] = v
        else:
            if isinstance(config[k], (list, tuple)):
                LOGGER.debug('Extending config["{}"]: {} with {}'.format(k, config[k], v))
                if isinstance(v, (list, tuple)):
                    config[k].extend(v)
                else:
                    config[k].append(v)
            else:
                LOGGER.debug('Overwriting config["{}"]: {} -> {}'.format(k, config[k], v))
                config[k] = v
    return config


def _load_py_experiment(script, spec, *, dump_dir):
    LOGGER.info('Found {} function in {}; will use it as experiments configuration generator'.format(spec, script))

    def _create_and_dump_config(spec_params, dump_dir):
        config_path = dump_dir / 'config.pkl'
        with open(config_path, "wb") as file:
            cloudpickle.dump(spec_params, file)
            
        return config_path

    experiments_list = get_experiments_list(script, spec)
    for experiment in experiments_list:
        spec_params = experiment.to_dict()
        spec_params['name'] = re.sub(r'[ .,_-]+', '-', spec_params['name'].lower())

        config_path = _create_and_dump_config(spec_params, dump_dir)

        yield config_path, spec_params


def generate_experiments(script, context, *, spec='spec', dump_dir=None):
    experiments = _load_py_experiment(script, spec=spec, dump_dir=dump_dir)

    for config_path, spec_params in experiments:
        experiment = _merge_experiment_parameters(spec_params, context)
        yield config_path, experiment


_experiment_list = None

def get_experiments_list(script, spec):
    global _experiment_list
    if _experiment_list is None:
        vars = {
            'script': str(Path(script).name),
            '__file__': str(Path(script)),
        }
        exec(open(script).read(), vars)
        _experiment_list = vars.get(spec, None)
        if _experiment_list is None:
            print("The expriement file was loaded but the {} "
                  "variable is not set. Exiting".format(spec))
            exit(1)

    return _experiment_list
