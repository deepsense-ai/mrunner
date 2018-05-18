# -*- coding: utf-8 -*-
import unittest

from path import tempdir, Path

from mrunner.config import Context
from mrunner.utils import DObject, get_paths_to_copy, PathToDump


class ConfigTestCase(unittest.TestCase):

    def test_on_missing_config_file(self):
        with tempdir() as tmp:
            config_path = tmp / 'config.yaml'
            config = ConfigParser(config_path).load()
            self.assertEqual({}, config.contexts)
            self.assertEqual('', config.current_context)
            self.assertTrue(not config_path.exists())


class UtilsTestCase(unittest.TestCase):

        # self.assertRaises(AttributeError, Foo.__new__, foo='bar')

    def test_paths_to_copy(self):
        with tempdir() as tmp:
            tmp.chdir()
            (tmp / 'a/1').makedirs()
            (tmp / 'a/2').makedirs()
            (tmp / 'b/1').makedirs()
            (tmp / 'b/2').makedirs()
            (tmp / 'c/1/a').makedirs()
            (tmp / 'file1').write_text('file1')
            (tmp / 'file2').write_text('file2')
            (tmp / 'file3').write_text('file3')
            (tmp / 'a/file_a1').write_text('file_a1')
            (tmp / 'a/1/file_a1_1').write_text('file_a1_1')

            # list all dirs and files
            self.assertEqual({PathToDump(Path(p), Path(p)) for p in {'a', 'b', 'c', 'file1', 'file2', 'file3'}},
                             set(get_paths_to_copy()))

            # exclude 'a' and 'file1'
            self.assertEqual({PathToDump(Path(p), Path(p)) for p in {'b', 'c', 'file2', 'file3'}},
                             set(get_paths_to_copy(exclude=['a', 'file1'])))

            # exclude 'a/1 and 'file1'
            self.assertEqual({PathToDump(Path(p), Path(p)) for p in {'a/2', 'a/file_a1', 'b', 'c', 'file2', 'file3'}},
                             set(get_paths_to_copy(exclude=['a/1', 'file1', 'a/10/file_a10_1'])))

            # add external resource
            self.assertEqual({PathToDump(Path(s), Path(d)) for s, d in {('../external1', 'external1'),
                                                                        ('a', 'a'), ('b', 'b'), ('c', 'c'),
                                                                        ('file1', 'file1'),
                                                                        ('file2', 'file2'),
                                                                        ('file3', 'file3')}},
                             set(get_paths_to_copy(paths_to_copy=[tmp / '../external1'])))
