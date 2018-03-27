import os
import tarfile
import tempfile

from fabric.api import run
from fabric.context_managers import cd
from fabric.contrib.project import rsync_project
from fabric.operations import put
from fabric.state import env

from mrunner.utils import id_generator


class PrometheusBackend(object):
    def __init__(self, username, host, scratch_space):
        self.host = host
        self.username = username
        self.host_string = '{username}@{host}'.format(username=self.username, host=self.host)
        self.scratch_space = scratch_space
        env['host_string'] = self.host_string
        self.mkdir(self.scratch_space)

    def _create_remote_script(self, command, script_name):
        script_name = script_name + '_' + id_generator(20) + '.sh'
        remote_path = os.path.join(self.scratch_space, script_name)

        with tempfile.NamedTemporaryFile(mode='w') as tmp_file:
            tmp_file.write('#!/usr/bin/env sh\n')
            tmp_file.write(command + '\n')
            tmp_file.flush()
            put(tmp_file.name, remote_path)

        run('chmod +x {path}'.format(path=remote_path))
        return remote_path

    def sbatch(self, task, partition='plgrid', time='24:00:00', cores=24, stdout_path='/dev/null', ntasks=1, gres=None,
               account=None):
        remote_path = self._create_remote_script(task.command, task.name)
        remote_command = 'sbatch -p {partition} -t {time} {gpu_gres} {account} -c {num_cores} -n {ntasks} -o {stdout_path} {script_path}'.format(
            partition=partition,
            time=time,
            num_cores=cores,
            stdout_path=stdout_path,
            gpu_gres=('--gres={}'.format(gres) if gres else ''),
            account=('-A {}'.format(account) if gres else ''),
            script_path=remote_path,
            ntasks=ntasks
        )
        print('remote_command=', remote_command)
        run(remote_command)

    def srun(self, task, partition='plgrid', cores=24, ntasks=1, gres=None, account=None):
        remote_path = self._create_remote_script(task.command, task.name)

        remote_command = 'srun -p {partition} {gpu_gres} {account} -c {num_cores} -n {ntasks} {script_path}'.format(
            partition=partition,
            gpu_gres=('--gres={}'.format(gres) if gres else ''),
            account=('-A {}'.format(account) if gres else ''),
            num_cores=cores,
            script_path=remote_path,
            ntasks=ntasks
        )
        print('remote_command=', remote_command)
        run(remote_command)

    def mkdir(self, path):
        run('mkdir -p {path}'.format(path=path))

    def copy_path(self, remote_path, local_path):
        rsync_project(remote_path, local_path)

    def copy_paths(self, paths_to_dump):
        for path_to_dump in paths_to_dump:
            remote_path_rel_parent = os.path.dirname(path_to_dump['dst_rel'])
            remote_path = os.path.join(path_to_dump['dst'], remote_path_rel_parent)
            self.copy_path(remote_path, path_to_dump['src'])

    def copy_paths_rel(self, paths_to_dump, dst_dir):

        print('copy_paths_rel')
        for d in paths_to_dump:
            print(d)

        with tempfile.NamedTemporaryFile(suffix='.tar.gz') as temp_file:
            print('tmp_path', temp_file.name)
            with tarfile.open(temp_file.name, 'w:gz') as tar_file:
                for d in paths_to_dump:
                    remote_rel_path, local_path = d['dst_rel'], d['src']
                    print('adding_path', local_path)
                    tar_file.add(local_path, arcname=remote_rel_path)

            print('dst_dir', dst_dir)
            self.copy_path(dst_dir, temp_file.name)
            with cd(dst_dir):
                run('tar xfz {tar_filename} && rm {tar_filename}'.format(
                    tar_filename=os.path.join(dst_dir, os.path.basename(temp_file.name))))


def parse_paths_to_dump(resource_dir_path, paths_to_dump_conf, paths_to_dump):
    if paths_to_dump_conf:
        paths_to_dump = [line.split(' ') for line in open(paths_to_dump_conf)]
    else:
        paths_to_dump = [(src, src) for path_to_dump_list in paths_to_dump
                         for src in path_to_dump_list.split(' ') if src]

    # relative path is required for name in archive which is prepared on slurm
    return [{'src': os.path.abspath(src), 'dst': resource_dir_path, 'dst_rel': dst_rel}
            for src, dst_rel in paths_to_dump]


if __name__ == '__main__':
    username = 'plghenrykm'
    host = 'pro.cyfronet.pl'

    prometheus = PrometheusBackend(username=username, host=host)
    # prometheus.sbatch('uptime', time='01:00:00', partition='plgrid-testing')

    command = 'echo test ; sleep 1; echo test2; sleep 1'
    # prometheus.srun('nvidia-smi', partition='plgrid-gpu')
    prometheus.srun(command, partition='plgrid-testing')
