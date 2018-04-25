# -*- coding: utf-8 -*-
import tempfile
import unittest

import six
import yaml

from mrunner.cmd import Cmd
from mrunner.neptune import NeptuneWrapperCmd


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
