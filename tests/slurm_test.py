# -*- coding: utf-8 -*-
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import contextmanager

from fabric.operations import run
from fabric.state import env
from paramiko import Agent
from path import Path

from mrunner.cli.config import Context
from mrunner.backends.slurm import SlurmBackend, ExperimentScript, ExperimentRunOnSlurm


class TmpCmd(object):

    @property
    def command(self):
        return 'python experiment1.py --foo bar'

    @property
    def env(self):
        return {'CMD_VAR': 2}


class FabricTestCase(unittest.TestCase):

    def setUp(self):
        # assume that openssh-server is installed and tester public key is added to own account
        env['host_string'] = '{}@localhost'.format(os.path.basename(os.path.expanduser('~')))

    def test_fabric_connection_to_localhost(self):
        assert Agent().get_keys(), "Add your private key to ssh agent using 'ssh-add' command"
        run('echo "Hello world"')


class SlurmTestCase(unittest.TestCase):

    def setUp(self):
        # assume that openssh-server is installed and tester public key is added to own account
        slurm_url = '{}@localhost'.format(os.path.basename(os.path.expanduser('~')))
        self.tmp_dir = Path(tempfile.mkdtemp())

        self.scratch_dir = self.tmp_dir / 'scratch'
        self.storage_dir = self.tmp_dir / 'storage'
        self.context = Context(slurm_url=slurm_url,
                               scratch_dir=self.scratch_dir,
                               storage=self.storage_dir,
                               partition='plgrid.py-testing',
                               user_id='jj',
                               modules_to_load='plgrid.py/tools/python/3.6.0 plgrid.py/tools/imagemagick/6.9.1')
        self.experiment = ExperimentRunOnSlurm(self.context, project='project-name',
                                               name='experiment-name',
                                               cmd=TmpCmd(), env={'EXPERIMENT_VAR': 3})

        self.paths_to_dump = [
            {'src': os.path.abspath('tests'), 'dst': self.tmp_dir, 'dst_rel': 'tests'},
            {'src': os.path.abspath('mrunner'), 'dst': self.tmp_dir, 'dst_rel': 'mrunner'},
            {'src': os.path.abspath('certs/cpascal'), 'dst': self.tmp_dir, 'dst_rel': 'certs/cpascal'},
        ]

    def tearDown(self):
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

    def test_expand_vars(self):
        os.environ['SCRATCH'] = '/tmp/scratch'
        os.environ['STORAGE'] = '/tmp/storage'

        context = Context(storage='$STORAGE/bar', scratch_dir='foo',
                          slurm_url=None, partition=None,
                          modules_to_load=None, user_id='jj')
        s = SlurmBackend(context=context)
        self.assertEqual(s.scratch_dir, '/tmp/scratch/foo')
        self.assertEqual(s.storage_dir, '/tmp/storage/bar')
        self.assertTrue(isinstance(s.scratch_dir, Path))
        self.assertTrue(isinstance(s.storage_dir, Path))

    def test_slurm_create_directories(self):
        s = SlurmBackend(self.context)
        s.ensure_directories(self.experiment)
        self.assertTrue(self.scratch_dir.exists())
        self.assertTrue(self.storage_dir.exists())

    def test_slurm_experiment_script_generation(self):
        context = Context(slurm_url=self.context.slurm_url,
                          scratch_dir='/tmp/scratch',
                          storage='/tmp/storage',
                          partition='plgrid.py-testing',
                          modules_to_load='plgrid.py/tools/python/3.6.0 plgrid.py/tools/imagemagick/6.9.1',
                          after_module_load_cmd='echo loaded',
                          venv='/tmp/home/.venvs/project',
                          env={'CONTEXT_VAR': '1'},
                          user_id='jj')

        experiment = ExperimentRunOnSlurm(context=context, cmd=TmpCmd(), env={'EXPERIMENT_VAR': 3})

        # because pykwalify reloads sys, thus causing error while debugging in pycharm
        # generate shell script
        with secure_stdout_context():
            script = ExperimentScript(context, experiment)
        script_payload = script.path.text()
        expected_script_regexp = "#!/usr/bin/env sh\n" \
                                 "set -e\n" \
                                 "cd /tmp/scratch/.*\n" \
                                 "module load plgrid.py/tools/python/3.6.0\n" \
                                 "module load plgrid.py/tools/imagemagick/6.9.1\n" \
                                 "echo loaded\n" \
                                 "source /tmp/home/.venvs/project/bin/activate\n" \
                                 "export .*\n" \
                                 "export .*\n" \
                                 "export .*\n" \
                                 "python experiment1.py --foo bar"

        self.assertRegexpMatches(script_payload, expected_script_regexp)

    def test_slurm_script_name(self):
        # because pykwalify reloads sys, thus causing error while debugging in pycharm
        # generate shell script
        with secure_stdout_context():
            script = ExperimentScript(self.context, self.experiment)
        self.assertRegexpMatches(script.script_name, 'jj_project-name_experiment-name_.*.sh')

    # check if venv is overwritten
    # ensure venv has no slash on end


@contextmanager
def secure_stdout_context():
    # because pykwalify reloads sys, thus causing error while debugging in pycharm
    stdout_tmp, stderr_tmp = sys.stdout, sys.stderr
    yield
    sys.stdout, sys.stderr = stdout_tmp, stderr_tmp
