# -*- coding: utf-8 -*-
import logging
from collections import namedtuple
from copy import copy
from distutils.version import LooseVersion

import six
from deepsense import version

LOGGER = logging.getLogger(__name__)

NEPTUNE_LOCAL_VERSION = LooseVersion(version.__version__)


class NeptuneConfigFileBase(object):
    # set of attributes is force by neptune v1 yaml format

    class Parameter(namedtuple('Parameter', 'name type default required')):

        @staticmethod
        def create(name, value):
            if isinstance(value, bool):
                type = 'boolean'
            elif isinstance(value, int):
                type = 'int'
            elif isinstance(value, float):
                type = 'double'
            else:
                type = 'string'
                value = str(value)
            return NeptuneConfigFileBase.Parameter(name, type, value, False)

    def __init__(self, project, name, parameters, tags=None, description=None, **kwargs):
        self._project = project
        self._name = name
        self._parameters = [self.Parameter.create(k, v) for k, v in parameters.items()]
        self._description = description
        self._tags = tags

    def dump(self, fh):
        import yaml
        yaml.dump(self._format_data(), fh, default_flow_style=False)

    def _format_data(self):
        raise NotImplementedError()


class NeptuneConfigFileV1(NeptuneConfigFileBase):
    # see http://neptune-docs.deepsense.codilime.com/versions/1.6/reference-guides/cli.html#configuration-files
    def _format_data(self):
        def format_parameter(p):
            return dict(p._asdict())

        data = {
            'name': self._name,
            'project': self._project,
            'parameters': [format_parameter(p) for p in self._parameters]
        }
        if self._description:
            data['description'] = self._description
        if self._tags:
            data['tags'] = self._tags
        return data


class NeptuneConfigFileV2(NeptuneConfigFileBase):
    # see: https://docs.neptune.ml/cli/config/
    def _format_data(self):
        def format_parameter(p):
            return p.default

        data = {
            'open-webbrowser': False,
            'name': self._name,
            'project': self._project,
            'parameters': {p.name: format_parameter(p) for p in self._parameters}
        }
        if self._description:
            data['description'] = self._description
        if self._tags:
            data['tags'] = self._tags
        return data


def load_neptune_config(neptune_config_path):
    from deepsense.neptune.common.config import neptune_config

    global_config = neptune_config.load_global_config()
    local_config = neptune_config.load_local_config(neptune_config_path) if neptune_config_path else {}
    neptune_config = neptune_config.NeptuneConfig(global_config=global_config, local_config=local_config)

    if len(neptune_config.name) > 16:
        raise ValueError('Neptune config "name" key (experiment name) shall be at most 16 chars long')

    config_dict = neptune_config.config_dict

    def _rename(d, k1, k2):
        if k1 in d:
            d[k2] = copy(d[k1])
            del d[k1]

    _rename(config_dict, 'host', 'neptune_host')
    _rename(config_dict, 'port', 'neptune_port')
    _rename(config_dict, 'username', 'neptune_username')
    _rename(config_dict, 'password', 'neptune_password')
    _rename(config_dict, 'paths-to-copy', 'paths_to_copy')

    return neptune_config.config_dict


class NeptuneWrapperCmd(object):

    def __init__(self, cmd, experiment_config_path, neptune_storage=None, additional_tags=None, paths_to_dump=None,
                 docker_image=None):
        self._cmd = cmd
        self._experiment_config_path = experiment_config_path
        self._additional_tags = additional_tags
        self._storage = neptune_storage
        self._paths_to_dump = paths_to_dump
        self._docker_image = docker_image

    @property
    def command(self):
        cmd = self._cmd.split(' ') if isinstance(self._cmd, six.string_types) else self._cmd
        while cmd[0].startswith('python'):
            cmd = cmd[1:]

        base_argv = ['neptune', 'run', '--config', str(self._experiment_config_path)]
        if NEPTUNE_LOCAL_VERSION.version[0] == 1:
            storage_arv = ['--storage', self._storage] if self._storage else []
            tags_argv = ['--tags'] + self._additional_tags if self._additional_tags else []
            # for v2 it is exclude param
            dump_argv = ['--paths-to-copy'] + self._paths_to_dump if self._paths_to_dump else []
            cmd = [cmd[0], '--'] + cmd[1:]
        else:
            storage_arv = []
            tags_argv = []
            for tag in self._additional_tags:
                tags_argv.extend(['--tag', tag])
            dump_argv = []
        docker_argv = ['--docker-image', self._docker_image] if self._docker_image else []

        cmd = base_argv + storage_arv + tags_argv + dump_argv + docker_argv + cmd
        return ' '.join(cmd)

    @property
    def env(self):
        # setup env variables to setup neptune config
        neptune_env = {}
        if NEPTUNE_LOCAL_VERSION.version[0] == 1:
            # neptune connection config is required because experiments from different neptune accounts may be
            # started on same system account
            config = self.conf
            assert config['username'], "Use ~/.neptune.yaml to setup credentials"
            assert config['password'], "Use ~/.neptune.yaml to setup credentials"

            neptune_env = {'NEPTUNE_PASSWORD': str(config['password']), 'NEPTUNE_USER': str(config['username'])}
            if 'host' in config:
                neptune_env['NEPTUNE_HOST'] = str(config['host'])
            if 'port' in config:
                neptune_env['NEPTUNE_PORT'] = str(config['port'])
        elif NEPTUNE_LOCAL_VERSION.version[0] == 2:
            neptune_env['HOME'] = '$(pwd)'  # neptune loads token from ~/.neptune_tokens/token

        # TODO: [PZ] because neptune env vars are set, maybe it is not required to set additional env var?
        neptune_env.update({'MRUNNER_UNDER_NEPTUNE': '1'})
        return neptune_env

    @property
    def conf(self):
        """Extracts neptune configuration from global config"""
        try:
            from deepsense.neptune.common.config import neptune_config
            global_config = neptune_config.load_global_config()
            # loads also NEPTUNE_* env vars
            return neptune_config.NeptuneConfig(global_config=global_config)
        except ImportError:
            raise RuntimeError('Install neptune-cli first and configure connection')
