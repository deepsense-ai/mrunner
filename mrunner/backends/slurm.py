# -*- coding: utf-8 -*-
import logging
import socket
import tarfile
import tempfile

import attr
from fabric.api import run as fabric_run
from fabric.context_managers import cd
from fabric.contrib.project import rsync_project
from fabric.state import env
from paramiko.agent import Agent
from path import Path

from mrunner.experiment import COMMON_EXPERIMENT_MANDATORY_FIELDS, COMMON_EXPERIMENT_OPTIONAL_FIELDS
from mrunner.plgrid import PLGRID_USERNAME, PLGRID_HOST, PLGRID_TESTING_PARTITION
from mrunner.utils.namesgenerator import id_generator
# from mrunner.utils.neptune import NeptuneToken
from mrunner.utils.utils import GeneratedTemplateFile, get_paths_to_copy, make_attr_class, filter_only_attr

LOGGER = logging.getLogger(__name__)
RECOMMENDED_CPUS_NUMBER = 4
DEFAULT_SCRATCH_SUBDIR = 'mrunner_scratch'
SCRATCH_DIR_RANDOM_SUFIX_SIZE = 10


def generate_experiment_scratch_dir(experiment):
    experiment_subdir = '{name}_{random_id}'.format(name=experiment.name,
                                                    random_id=id_generator(SCRATCH_DIR_RANDOM_SUFIX_SIZE))
    project_subdir = generate_project_scratch_dir(experiment)
    return project_subdir / experiment_subdir


def generate_project_scratch_dir(experiment):
    project_subdir = '{user_id}_{project}'.format(user_id=experiment.user_id, project=experiment.project)
    scratch_subdir = (experiment.scratch_subdir or DEFAULT_SCRATCH_SUBDIR)
    return Path(experiment._slurm_scratch_dir) / scratch_subdir / project_subdir


EXPERIMENT_MANDATORY_FIELDS = [
    ('venv', dict()),  # path to virtual environment
    ('user_id', dict()),  # used to generate project scratch dir
    ('_slurm_scratch_dir', dict())  # obtained from cluster $SCRATCH env
]

EXPERIMENT_OPTIONAL_FIELDS = [
    # by default use plgrid configuration
    ('slurm_url', dict(default='{}@{}'.format(PLGRID_USERNAME, PLGRID_HOST))),
    ('partition', dict(default=PLGRID_TESTING_PARTITION)),

    # scratch directory related
    ('scratch_subdir', dict(default='')),
    ('project_scratch_dir', dict(default=attr.Factory(generate_project_scratch_dir, takes_self=True))),
    ('experiment_scratch_dir', dict(default=attr.Factory(generate_experiment_scratch_dir, takes_self=True))),

    # run time related
    ('account', dict(default=None)),
    ('log_output_path', dict(default=None)),
    ('time', dict(default=None)),
    ('ntasks', dict(default=None)),
    ('modules_to_load', dict(default=attr.Factory(list), type=list)),
    ('after_module_load_cmd', dict(default='')),
    ('cmd_type', dict(default='srun')),
]

EXPERIMENT_FIELDS = COMMON_EXPERIMENT_MANDATORY_FIELDS + EXPERIMENT_MANDATORY_FIELDS + \
                    COMMON_EXPERIMENT_OPTIONAL_FIELDS + EXPERIMENT_OPTIONAL_FIELDS

ExperimentRunOnSlurm = make_attr_class('ExperimentRunOnSlurm', EXPERIMENT_FIELDS, frozen=True)


class ExperimentScript(GeneratedTemplateFile):
    DEFAULT_SLURM_EXPERIMENT_SCRIPT_TEMPLATE = 'slurm_experiment.sh.jinja2'

    def __init__(self, experiment):
        # merge env vars
        env = experiment.cmd.env.copy() if experiment.cmd else {}
        env.update(experiment.env)
        env = {k: str(v) for k, v in env.items()}

        experiment = attr.evolve(experiment, env=env, experiment_scratch_dir=experiment.experiment_scratch_dir)

        super(ExperimentScript, self).__init__(template_filename=self.DEFAULT_SLURM_EXPERIMENT_SCRIPT_TEMPLATE,
                                               experiment=experiment)
        self.experiment = experiment
        self.path.chmod('a+x')

    @property
    def script_name(self):
        e = self.experiment
        return '{}.sh'.format(e.experiment_scratch_dir.relpath(e.project_scratch_dir))


class SlurmWrappersCmd(object):

    def __init__(self, experiment, script_path):
        self._experiment = experiment
        self._script_path = script_path

    @property
    def command(self):
        # see: https://slurm.schedmd.com/srun.html
        # see: https://slurm.schedmd.com/sbatch.html

        if not self._cmd:
            raise RuntimeError('Instantiate one of SlurmWrapperCmd subclasses')

        cmd_items = [self._cmd]

        def _extend_cmd_items(cmd_items, option, data_key, default=None):
            value = self._getattr(data_key)
            if value:
                cmd_items += [option, str(value)]
            elif default:
                cmd_items += [option, default]

        default_log_path = self._experiment.experiment_scratch_dir / 'slurm.log' if self._cmd == 'sbatch' else None
        _extend_cmd_items(cmd_items, '-A', 'account')
        _extend_cmd_items(cmd_items, '-o', 'log_output_path', default_log_path)  # output
        _extend_cmd_items(cmd_items, '-p', 'partition')
        _extend_cmd_items(cmd_items, '-t', 'time')
        # _extend_cmd_items(cmd_items, '-n', 'ntasks')

        cmd_items += self._resources_items()
        cmd_items += [self._script_path]

        return ' '.join(cmd_items)

    def _getattr(self, key):
        return getattr(self, key, getattr(self._experiment, key) or None)

    def _resources_items(self):
        """mapping from mrunner notation into slurm"""
        cmd_items = []
        mrunner_resources = self._getattr('resources')
        for resource_type, resource_qty in mrunner_resources.items():
            if resource_type == 'cpu':
                ntasks = int(self._getattr('ntasks') or 1)
                cores_per_task = int(int(resource_qty) / ntasks)
                cmd_items += ['-c', str(cores_per_task)]

                if ntasks > 1:
                    cmd_items += ['-n', str(ntasks)]
                    LOGGER.debug('Running {} tasks'.format(ntasks))
                total_cpus = cores_per_task * ntasks
                if total_cpus != int(resource_qty):
                    LOGGER.warning('Will request {} CPU instead of {}'.format(total_cpus, int(resource_qty)))
                if total_cpus > RECOMMENDED_CPUS_NUMBER:
                    LOGGER.warning('Requested number of CPU is higher than recommended value {}/4'.format(
                        total_cpus, RECOMMENDED_CPUS_NUMBER))
                LOGGER.debug('Using {}/{} CPU cores per_task/total'.format(cores_per_task, total_cpus))
            elif resource_type == 'gpu':
                cmd_items += ['--gres', 'gpu:{}'.format(resource_qty)]
                LOGGER.debug('Using {} gpu'.format(resource_qty))
            elif resource_type == 'mem':
                cmd_items += ['--mem', str(resource_qty)]
                LOGGER.debug('Using {} memory'.format(resource_qty))
            else:
                raise ValueError('Unsupported resource request: {}={}'.format(resource_type, resource_qty))

        return cmd_items


class SBatchWrapperCmd(SlurmWrappersCmd):

    def __init__(self, experiment, script_path, **kwargs):
        super(SBatchWrapperCmd, self).__init__(experiment, script_path, **kwargs)
        self._cmd = 'sbatch'


class SRunWrapperCmd(SlurmWrappersCmd):

    def __init__(self, experiment, script_path, **kwargs):
        super(SRunWrapperCmd, self).__init__(experiment, script_path, **kwargs)
        self._cmd = 'srun'


# class SlurmNeptuneToken(NeptuneToken):
#
#     def __init__(self, experiment):
#         # TODO: need refactor other part of code - here expereiment can be dict or backend specific object
#         user_id = experiment['user_id'] if isinstance(experiment, dict) else experiment.user_id
#         profile_name = '{}-{}'.format(user_id, socket.gethostname())
#         super(SlurmNeptuneToken, self).__init__(profile=profile_name)
#

class SlurmBackend(object):

    def run(self, experiment):
        assert Agent().get_keys(), "Add your private key to ssh agent using 'ssh-add' command"

        # configure fabric
        slurm_url = experiment.pop('slurm_url', '{}@{}'.format(PLGRID_USERNAME, PLGRID_HOST))
        env['host_string'] = slurm_url
        slurm_scratch_dir = experiment['storage_dir']
        experiment = ExperimentRunOnSlurm(slurm_scratch_dir=slurm_scratch_dir, slurm_url=slurm_url,
                                          **filter_only_attr(ExperimentRunOnSlurm, experiment))
        LOGGER.debug('Configuration: {}'.format(experiment))

        self.ensure_directories(experiment)
        self.deploy_neptune_token(experiment=experiment)
        script_path = self.deploy_code(experiment)
        SCmd = {'sbatch': SBatchWrapperCmd, 'srun': SRunWrapperCmd}[experiment.cmd_type]
        cmd = SCmd(experiment=experiment, script_path=script_path)
        self._fabric_run(cmd.command)

    def ensure_directories(self, experiment):
        self._ensure_dir(experiment.experiment_scratch_dir)
        self._ensure_dir(experiment.storage_dir)

    def deploy_code(self, experiment):
        paths_to_dump = get_paths_to_copy(exclude=experiment.exclude, paths_to_copy=experiment.paths_to_copy)
        with tempfile.NamedTemporaryFile(suffix='.tar.gz') as temp_file:
            # archive all files
            with tarfile.open(temp_file.name, 'w:gz') as tar_file:
                for p in paths_to_dump:
                    LOGGER.debug('Adding "{}" to deployment archive'.format(p.rel_remote_path))
                    tar_file.add(p.local_path, arcname=p.rel_remote_path)

            # upload archive to cluster and extract
            self._put(temp_file.name, experiment.experiment_scratch_dir)
            with cd(experiment.experiment_scratch_dir):
                archive_remote_path = experiment.experiment_scratch_dir / Path(temp_file.name).name
                self._fabric_run('tar xf {tar_filename} && rm {tar_filename}'.format(tar_filename=archive_remote_path))

        # create and upload experiment script
        script = ExperimentScript(experiment)
        remote_script_path = experiment.project_scratch_dir / script.script_name
        self._put(script.path, remote_script_path)

        return remote_script_path

    def deploy_neptune_token(self, experiment):
        return
        #TODO(pm): remove me please
        if experiment.local_neptune_token:
            remote_token = SlurmNeptuneToken(experiment=experiment)
            self._ensure_dir(remote_token.path.parent)
            self._put(experiment.local_neptune_token.path, remote_token.path)

    @staticmethod
    def _put(local_path, remote_path, quiet=True):
        quiet_kwargs = {'ssh_opts': '-q', 'extra_opts': '-q'} if quiet else {}
        rsync_project(remote_path, local_path, **quiet_kwargs)

    @staticmethod
    def _ensure_dir(directory_path):
        SlurmBackend._fabric_run('mkdir -p {path}'.format(path=directory_path))

    @staticmethod
    def _fabric_run(cmd):
        return fabric_run(cmd)
