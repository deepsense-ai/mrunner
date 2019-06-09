# -*- coding: utf-8 -*-
import logging
import random
import re
import warnings

import attr
import six
from path import Path
import cloudpickle

from mrunner.utils.namesgenerator import id_generator, get_random_name
# from mrunner.utils.neptune import NeptuneConfigFileV1, NeptuneConfigFileV2, load_neptune_config, NEPTUNE_LOCAL_VERSION, \
#     NeptuneToken

LOGGER = logging.getLogger(__name__)

COMMON_EXPERIMENT_MANDATORY_FIELDS = [
    ('backend_type', dict()),
    ('name', dict()),
    ('storage_dir', dict()),
    ('cmd', dict())
]

COMMON_EXPERIMENT_OPTIONAL_FIELDS = [
    ('project', dict(default='sandbox')),
    ('requirements', dict(default=attr.Factory(list), type=list)),
    ('exclude', dict(default=None, type=list)),
    ('paths_to_copy', dict(default=attr.Factory(list), type=list)),
    ('env', dict(default=attr.Factory(dict), type=dict)),
    ('resources', dict(default=attr.Factory(dict), type=dict)),
    ('cwd', dict(default=attr.Factory(Path.getcwd))),
]


class Experiment(object):

    def __init__(self, project, name, script, parameters, **kwargs):
        def _get_arg(k, sep=' '):
            list_type = ['tags', 'paths-to-copy', 'exclude', 'properties', 'python_path']
            v = kwargs.pop(k, [] if k in list_type else '')
            return v.split(sep) if isinstance(v, six.string_types) and k in list_type else v

        self.script = script
        self.project = project
        self.name = name[:16]
        self.parameters = parameters

        self.env = kwargs.pop('env', {})
        self.env['PYTHONPATH'] = ':'.join(['$PYTHONPATH', ] + _get_arg('python_path', sep=':'))

        for k in list(kwargs.keys()):
            self.__setattr__(k, _get_arg(k))

    def to_dict(self):
        return self.__dict__


class NeptuneExperiment(object):
    """Use Experiment class instead"""

    def __init__(self, what, tags, pythonpath, paths_to_dump, name, project_name, parameters,
                 random_id=None, description=None):
        warnings.warn('User Experiment class instead', category=DeprecationWarning, stacklevel=2)
        self.what = what
        self.tags = tags
        # self.pythonpath = pythonpath
        self.env = {'PYTHONPATH': '$PYTHONPATH:{}'.format(pythonpath)}
        self.paths_to_dump = paths_to_dump.split(' ') if isinstance(paths_to_dump, str) else paths_to_dump
        self.name = name[:16]
        self.project_name = project_name
        self.parameters = parameters
        self.description = description or name
        self.random_id = "{}".format(random.randint(100000, 999999)) if not random_id else random_id

    def to_dict(self):
        attribute_map = {
            'what': 'script', 'project_name': 'project', 'paths_to_dump': 'paths_to_copy'
        }
        return {attribute_map.get(k, k): v for k, v in self.__dict__.items()}


def merge_experiment_parameters(cli_kwargs, neptune_config, context):
    config = context.copy()
    for k, v in list(neptune_config.items()) + list(cli_kwargs.items()):
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


def _load_py_experiment_and_generate_neptune_yamls(script, spec, *, neptune_dir, neptune_version=None):
    LOGGER.info('Found {} function in {}; will use it as experiments configuration generator'.format(spec, script))
    neptune_support = bool(neptune_dir)
    # TODO(pm): This is to be refactored
    neptune_support = False
    if neptune_support:
        if neptune_version and NEPTUNE_LOCAL_VERSION < neptune_version:
            # this shall match because we'll later use local neptune to parse them
            raise RuntimeError('Current neptune major version: {}, doesn\'t match forced one: {}'.format(
                NEPTUNE_LOCAL_VERSION, neptune_version
            ))
        NeptuneConfigFile = {'1': NeptuneConfigFileV1, '2': NeptuneConfigFileV2}[str(NEPTUNE_LOCAL_VERSION.version[0])]

    def _dump_to_neptune(cli_params, neptune_dir):
        neptune_path = None
        while not neptune_path or neptune_path.exists():
            neptune_path = neptune_dir / 'neptune-{}-{}.yaml'.format(get_random_name(), id_generator(4))
        with neptune_path.open('w') as neptune_file:
            NeptuneConfigFile(**cli_params).dump(neptune_file)
        LOGGER.debug('Generated neptune file {}: {}'.format(neptune_path, Path(neptune_path).text()))
        return neptune_path

    def _new_dump(cli_params, neptune_dir):
        config_path = neptune_dir / 'config-{}-{}.pkl'.format(get_random_name(), id_generator(4))

        with open(config_path, "wb") as file:
            cloudpickle.dump(cli_params, file)
        return config_path


    experiments_list = get_experiments_list(script, spec)
    for experiment in experiments_list:
        if isinstance(experiment, dict):
            experiment = NeptuneExperiment(**experiment)
        elif not hasattr(experiment, 'to_dict'):
            experiment = NeptuneExperiment(**experiment.__dict__)
        cli_params = experiment.to_dict()

        #TODO(pm): remove me please
        # neptune_path = _dump_to_neptune(cli_params, neptune_dir) if neptune_support else None
        neptune_path = _new_dump(cli_params, neptune_dir)

        # TODO: possibly part of this shall not be removed on experiments without neptune support
        cli_params.pop('parameters', None)
        cli_params.pop('project', None)
        cli_params.pop('description', None)
        cli_params.pop('tags', None)
        cli_params.pop('random_id', None)

        yield (neptune_path, cli_params)


def generate_experiments(script, neptune, context, *, spec='spec',
                         neptune_dir=None, neptune_version=None, **cli_kwargs):
    experiments = _load_py_experiment_and_generate_neptune_yamls(script, spec=spec,
                                                                 neptune_dir=neptune_dir,
                                                                 neptune_version=neptune_version)

    for neptune_path, cli_kwargs_ in experiments:
        cli_kwargs_['name'] = re.sub(r'[ .,_-]+', '-', cli_kwargs_['name'].lower())
        cli_kwargs_['cwd'] = Path.getcwd()

        # neptune_config = load_neptune_config(neptune_path) if neptune_path else {}
        # del neptune_config['storage']

        neptune_config = {}
        cli_kwargs_.update(**cli_kwargs)
        experiment = merge_experiment_parameters(cli_kwargs_, neptune_config, context)

        yield neptune_path, experiment


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
