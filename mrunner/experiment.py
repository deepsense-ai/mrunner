# -*- coding: utf-8 -*-

from mrunner.utils import DObject


class Experiment(DObject):

    @property
    def cmd_without_params(self):
        cmd = self.cmd.command.split(' -- ')[0] + ' --' if self.cmd else ''
        return cmd.split(' ')

    @property
    def params(self):
        cmd = self.cmd.command.split(' -- ')[1] if self.cmd else ''
        return cmd.split(' ')

    @property
    def all_env(self):
        envs = dict(self.env)
        envs.update(self.cmd.env if self.cmd else {})
        return envs
