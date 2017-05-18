import hashlib
import os
import os.path as osp
import tarfile
from fabric.api import run
from fabric.context_managers import cd
from fabric.contrib.project import rsync_project
from fabric.operations import put
from fabric.state import env

from mrunner.utils import id_generator


class Prometheus(object):
    def __init__(self, username, host, scratch_space):
        self.host = host
        self.username = username
        self.host_string = '{username}@{host}'.format(username=self.username, host=self.host)
        self.scratch_space = scratch_space
        env['host_string'] = self.host_string
        self.mkdir(self.scratch_space)

    def _make_script_name(self):
        return 'mrunner_batch_' + id_generator(20) + '.sh'

    def _chmod_x(self, path):
        run('chmod +x {path}'.format(path=path))

    def _create_remote_script(self, command):
        script_name = self._make_script_name()
        script_path = osp.join('/tmp/', script_name)

        with open(script_path, 'w') as f:
            print >> f, '#!/bin/bash'
            print >> f, command

        remote_path = osp.join('mrunner/batch_scripts/', script_name)
        put(script_path, remote_path)
        self._chmod_x(remote_path)
        return remote_path

    def _construct_command(self, task):
        command = ''
        if task.cwd is not None:
            command += 'cd {cwd}\n'.format(cwd=task.cwd)

        command += 'module load test/pro-viz/1.0\n'
        command += 'module load plgrid/tools/ffmpeg/3.0\n'
        command += 'module load plgrid/tools/python/2.7.13\n'

        if task.venv_path is not None:
            command += 'source {venv_path}/bin/activate\n'.format(venv_path=task.venv_path)

        for name, val in task.env.iteritems():
            command += 'export {name}={val}\n'.format(name=name, val=val)
        command += task.command
        return command

    def sbatch(self, task, partition='plgrid', time='24:00:00', cores=24, stdout_path='/dev/null'):
        command = self._construct_command(task)
        remote_path = self._create_remote_script(command)
        remote_command = 'sbatch -p {partition} -t {time} {gpu_gres} -c {num_cores} -o {stdout_path} {script_path}'.format(partition=partition,
                                                                  time=time,
                                                                  num_cores=cores,
                                                                  stdout_path=stdout_path,
                                                                  gpu_gres=('--gres=gpu' if partition == 'plgrid-gpu' else ''),
                                                                  script_path=remote_path
                                                                )
        print 'remote_command=', remote_command
        run(remote_command)

    def srun(self, task, partition='plgrid', cores=24):
        command = self._construct_command(task)
        remote_path = self._create_remote_script(command)

        remote_command = 'srun -p {partition} {gpu_gres} -c {num_cores} {script_path}'.format(partition=partition,
                                                            gpu_gres=('--gres=gpu' if partition == 'plgrid-gpu' else ''),
                                                            num_cores=cores,
                                                            script_path=remote_path
                                                            )
        print 'remote_command=', remote_command
        run(remote_command)

    def mkdir(self, path):
        run('mkdir -p {path}'.format(path=path))

    def copy_paths(self, paths_to_dump):
        for d in paths_to_dump:
            remote_path, local_path = d['dst'], d['src']
            self.copy_path(remote_path, local_path)
            #put(local_path, remote_path)

    def copy_paths_rel(self, paths_to_dump, dst_dir):
        tar_filename = '{id}.tar.gz'.format(id=id_generator(20))
        tar_tmp_path = os.path.join('/tmp/', tar_filename)
        print 'tmp_path', tar_tmp_path
        tar = tarfile.open(tar_tmp_path, 'w:gz')

        for d in paths_to_dump:
            remote_rel_path, local_path = d['dst_rel'], d['src']
            if remote_rel_path != '':
                raise NotImplementedError
            print 'adding_path', local_path
            tar.add(local_path, arcname=os.path.basename(local_path))
        tar.close()

        print 'dst_dir', dst_dir
        self.copy_path(dst_dir, tar_tmp_path)
        with cd(dst_dir):
            run('ls *')
            run('tar xfz {tar_filename}'.format(tar_filename=tar_filename))

    def copy_paths_rel_cached(self, paths_to_dump, dst_dir):
        raise NotImplementedError
        tar_filename = '{id}.tar.gz'.format(id=id_generator(20))
        tar_path = os.path.join('/tmp/', tar_filename)
        print 'tmp_path', tar_path
        tar = tarfile.open(tar_path, 'w:gz')

        for d in paths_to_dump:
            remote_rel_path, local_path = d['dst_rel'], d['src']
            if remote_rel_path != '':
                raise NotImplementedError
            print 'adding_path', local_path
            tar.add(local_path, arcname=os.path.basename(local_path))
        tar.close()
        sha_digest = self._sha256_file(tar_path)
        print sha_digest

        print 'dst_dir', dst_dir

        # WARNING(maciek): this is not concurrent safe

        remote_tar_filename = sha_digest + '.tar.gz'
        if not exists(osp.join(self.scratch_space, remote_tar_filename)):
            self.copy_path(osp.join(self.scratch_space, remote_tar_filename), tar_path)

        run('cp {path_src} {path_dst}'.format(path_src=osp.join(self.scratch_space, remote_tar_filename),
                                              path_dst=osp.join(dst_dir, remote_tar_filename)))

        with cd(dst_dir):
            run('ls *')
            run('tar xfz {remote_tar_filename}'.format(remote_tar_filename=remote_tar_filename))

    def _sha256_file(self, path):
        return hashlib.sha256(open(path, 'rb').read()).hexdigest()


    def copy_path(self, remote_path, local_path):
        rsync_project(remote_path, local_path)




if __name__ == '__main__':

    username = 'plghenrykm'
    host = 'pro.cyfronet.pl'

    prometheus = Prometheus(username=username, host=host)
    #prometheus.sbatch('uptime', time='01:00:00', partition='plgrid-testing')

    command = 'echo test ; sleep 1; echo test2; sleep 1'
    #prometheus.srun('nvidia-smi', partition='plgrid-gpu')
    prometheus.srun(command, partition='plgrid-testing')

