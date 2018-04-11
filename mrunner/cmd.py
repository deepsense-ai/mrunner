# -*- coding: utf-8 -*-
import logging

LOGGER = logging.getLogger(__name__)


class Cmd(object):

    def __init__(self, cmd, exp_dir_path=None):
        self._cmd = cmd
        self._exp_dir_path = exp_dir_path

    @property
    def command(self):
        return ' '.join(self._cmd)

    @property
    def env(self):
        return {'MRUNNER_EXP_DIR_PATH': self._exp_dir_path, 'MRUNNER_UNDER_NEPTUNE': '0'}


class YamlCmd(object):

    def __init__(self, cmd, experiment_config_path, neptune_storage=None, additional_tags=None, paths_to_dump=None,
                 exp_dir_path=None):
        self._cmd = cmd
        self._experiment_dir_path = exp_dir_path
        self._experiment_config_path = experiment_config_path
        self._additional_tags = additional_tags
        self._storage = neptune_storage
        self._paths_to_dump = paths_to_dump

    @property
    def command(self):
        base_argv = self._cmd + ['--config', self._experiment_config_path]
        tags_argv = ['--tags'] + self._additional_tags if self._additional_tags else []
        dump_argv = ['--paths-to-copy'] + self._paths_to_dump if self._paths_to_dump else []
        storage_arv = ['--storage', self._storage] if self._storage else []

        cmd = base_argv + storage_arv + tags_argv + dump_argv + ['--']
        return ' '.join(cmd)

    @property
    def env(self):
        return {'MRUNNER_EXP_DIR_PATH': self._experiment_dir_path, 'MRUNNER_UNDER_NEPTUNE': '0'}


class PlgridScript(object):

    def __init__(self, cmd, cwd=None, env=None, modules_to_load=None, venv_path=None,
                 after_module_load_cmd=None, script_name="mrunner"):
        self._cmd = cmd
        self._working_dir = cwd
        self._env = (env or {}).copy()
        self._modules_to_load = modules_to_load or []
        self._after_module_cmd_load_cmd = after_module_load_cmd
        self._venv_path = venv_path
        self._script_name = script_name

    @property
    def command(self):
        lines = ['set -e', ]
        if self._working_dir:
            lines.append('cd ' + self._working_dir)
        lines.extend(['module load ' + module for module in self._modules_to_load])
        if self._after_module_cmd_load_cmd:
            lines.append(self._after_module_cmd_load_cmd)
        if self._venv_path:
            lines.append('source %s/bin/activate' % self._venv_path)
        lines.extend(['export %s=%s' % (k, str(v)) for k, v in self._env.items()])
        lines.append(self._cmd)
        return '\n'.join(lines)

    @property
    def env(self):
        return self._env

    @property
    def name(self):
        return self._script_name


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
        cmd = self._cmd.split(' ') if isinstance(self._cmd, str) else self._cmd
        while cmd[0].startswith('python'):
            cmd = cmd[1:]

        base_argv = ['neptune', 'run', cmd[0], '--config', self._experiment_config_path]
        tags_argv = ['--tags'] + self._additional_tags if self._additional_tags else []
        dump_argv = ['--paths-to-copy'] + self._paths_to_dump if self._paths_to_dump else []
        storage_arv = ['--storage', self._storage] if self._storage else []
        docker_argv = ['--docker-image', self._docker_image] if self._docker_image else []

        cmd = base_argv + storage_arv + tags_argv + dump_argv + docker_argv + ['--'] + cmd[1:]
        return ' '.join(cmd)

    @property
    def env(self):

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
