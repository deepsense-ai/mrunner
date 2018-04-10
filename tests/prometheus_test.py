# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
import unittest

from fabric.operations import run
from fabric.state import env

from mrunner.prometheus import PrometheusBackend, parse_paths_to_dump


class PrometheusTestCase(unittest.TestCase):

    def setUp(self):
        # assume that openssh-server is installed and tester public key is added to own account
        self.username = os.path.basename(os.path.expanduser('~'))
        self.tmp_dir = tempfile.mkdtemp()
        self.paths_to_dump = [
            {'src': os.path.abspath('tests'), 'dst': self.tmp_dir, 'dst_rel': 'tests'},
            {'src': os.path.abspath('mrunner'), 'dst': self.tmp_dir, 'dst_rel': 'mrunner'},
            {'src': os.path.abspath('certs/cpascal'), 'dst': self.tmp_dir, 'dst_rel': 'certs/cpascal'},
        ]
        env['host_string'] = '{username}@{host}'.format(username=self.username, host='localhost')

    def tearDown(self):
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

    def test_fabric_connection_to_localhost(self):
        run('echo "Hello world"')

    def test_fabric_copy_path(self):
        p = PrometheusBackend(self.username, 'localhost', scratch_space=self.tmp_dir)
        # shall copy tests directory into temp_dir (i.e. new directory /tmp/<random>/tests shall be created)
        p.copy_path(self.tmp_dir, 'tests')
        local_entries = [os.path.join(root, filename) for root, dirs, files in os.walk('tests') for filename in files]
        remote_entries = [os.path.relpath(os.path.join(root, filename), self.tmp_dir)
                          for root, dirs, files in os.walk(self.tmp_dir) for filename in files]
        self.assertEqual(local_entries, remote_entries)

    def test_fabric_copy_paths(self):
        p = PrometheusBackend(self.username, 'localhost', scratch_space=self.tmp_dir)
        p.copy_paths(self.paths_to_dump)
        local_entries, remote_entries = self._get_dirs_entries('.', self.tmp_dir)
        self.assertEqual(local_entries, remote_entries)

    def test_fabric_copy_paths_rel(self):
        p = PrometheusBackend(self.username, 'localhost', scratch_space=self.tmp_dir)
        p.copy_paths_rel(self.paths_to_dump, self.tmp_dir)
        local_entries, remote_entries = self._get_dirs_entries('.', self.tmp_dir)
        self.assertEqual(local_entries, remote_entries)

    def _get_dirs_entries(self, local_root, remote_root):
        local_entries = sorted([os.path.relpath(os.path.join(root, filename), local_root)
                                for entry in self.paths_to_dump
                                for root, dirs, files in os.walk(entry['src']) for filename in files])
        remote_entries = sorted([os.path.relpath(os.path.join(root, filename), remote_root)
                                 for root, dirs, files in os.walk(remote_root) for filename in files])
        return local_entries, remote_entries

    def test_parse_paths_to_dump(self):
        paths = parse_paths_to_dump('/tmp/storage', paths_to_dump_conf=None,
                                    paths_to_dump=['foo bar', 'src1 src/inner'])
        paths_expected = [
            {'src': os.path.abspath('foo'), 'dst': '/tmp/storage', 'dst_rel': 'foo'},
            {'src': os.path.abspath('bar'), 'dst': '/tmp/storage', 'dst_rel': 'bar'},
            {'src': os.path.abspath('src1'), 'dst': '/tmp/storage', 'dst_rel': 'src1'},
            {'src': os.path.abspath('src/inner'), 'dst': '/tmp/storage', 'dst_rel': 'src/inner'},
        ]
        self.assertEqual(paths_expected, paths)
