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
