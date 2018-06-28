# -*- coding: utf-8 -*-
import tempfile
import unittest

import six
import yaml
from path import tempdir

from mrunner.cmd import Cmd
from mrunner.utils.neptune import NeptuneWrapperCmd, NeptuneConfigFileV1, load_neptune_config, NeptuneConfigFileV2


class NeptuneWrapperCmdTestCase(unittest.TestCase):

    def test_cmd_generation(self):
        self.assertEqual(NeptuneWrapperCmd('python exp1.py --param1 value1 -f', experiment_config_path='foo.yaml',
                                           neptune_storage='/tmp/storage').command,
                         'neptune run exp1.py --config foo.yaml --storage /tmp/storage -- --param1 value1 -f')
        self.assertEqual(NeptuneWrapperCmd('./exp1.py --param1 value1 -f', experiment_config_path='foo.yaml',
                                           neptune_storage='/tmp/storage').command,
                         'neptune run ./exp1.py --config foo.yaml --storage /tmp/storage -- --param1 value1 -f')
        self.assertEqual(NeptuneWrapperCmd('./exp1.py --param1 value1 -f', experiment_config_path='foo.yaml',
                                           additional_tags=['tag1', 'tag2', 'tag3'],
                                           neptune_storage='/tmp/storage').command,
                         'neptune run ./exp1.py --config foo.yaml --storage /tmp/storage '
                         '--tags tag1 tag2 tag3 -- --param1 value1 -f')

    def test_env_generation(self):
        with tempfile.NamedTemporaryFile(suffix='.yaml') as config_file:
            yaml.dump({'user': 'foo@bar.com', 'password': 'foobar'})
            cmd = NeptuneWrapperCmd('python exp1.py --param1 value1 -f', experiment_config_path=config_file.name,
                                    neptune_storage='/tmp/storage')

            vars_with_no_str_values = {k: v for k, v in cmd.env.items() if not isinstance(v, six.string_types)}
            self.assertTrue(not vars_with_no_str_values)
            self.assertIn('NEPTUNE_PASSWORD', cmd.env)
            self.assertIn('NEPTUNE_USER', cmd.env)

            cmd = Cmd('python exp1.py --param1 value1 -f', exp_dir_path='/tmp/storage')
            vars_with_no_str_values = {k: v for k, v in cmd.env.items() if not isinstance(v, six.string_types)}
            self.assertTrue(not vars_with_no_str_values)
            self.assertNotIn('NEPTUNE_PASSWORD', cmd.env)
            self.assertNotIn('NEPTUNE_USER', cmd.env)


class NeptuneConfigFileTestCase(unittest.TestCase):
    CONFIG_ORIG = {
        'project': 'project',
        'name': 'name',
        'parameters': {'param1': 'param1', 'param2': 2, 'param3': True, 'param4': 1.2},
        'tags': ['tag1', 'tag2', 'tag3']
    }

    def test_generate_v1(self):
        from deepsense.version import __version__
        version = int(__version__.split('.')[0])
        if version == 1:
            # test only if neptune-cli==1 is installed
            with tempdir() as d:
                temp_path = d / 'neptune.yaml'
                with temp_path.open('w') as fh:
                    NeptuneConfigFileV1(**self.CONFIG_ORIG).dump(fh)
                config_read = load_neptune_config(temp_path)
            # trim to keys from config_orig
            config_trimmed = {k: v for k, v in config_read.items() if k in self.CONFIG_ORIG}

            # convert from v1 parameters list to dict
            config_trimmed['parameters'] = {d['name']: d['default'] for d in config_trimmed['parameters']}
            config_trimmed['tags'] = sorted(config_trimmed['tags'])  # not sure why order of tags is not preserved

            self.assertEqual(self.CONFIG_ORIG, config_trimmed)

    def test_generate_v2(self):
        from deepsense.version import __version__
        version = int(__version__.split('.')[0])
        if version == 2:
            # test only if neptune-cli==2 is installed
            with tempdir() as d:
                temp_path = d / 'neptune.yaml'
                with temp_path.open('w') as fh:
                    NeptuneConfigFileV2(**self.CONFIG_ORIG).dump(fh)
                config_read = load_neptune_config(temp_path)
            # trim to keys from config_orig
            config_trimmed = {k: v for k, v in config_read.items() if k in self.CONFIG_ORIG}
            self.assertEqual(self.CONFIG_ORIG, config_trimmed)

    def test_generate_extended_args(self):
        config_orig = self.CONFIG_ORIG.copy()
        config_orig['foo'] = 1
        config_orig['bar'] = 2
        config = NeptuneConfigFileV1(**config_orig)
