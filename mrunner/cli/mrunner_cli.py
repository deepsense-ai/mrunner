#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import click
from path import Path

from mrunner.backends.k8s import KubernetesBackend
from mrunner.backends.slurm import SlurmBackend#, SlurmNeptuneToken
from mrunner.cli.config import ConfigParser, context as context_cli
from mrunner.experiment import generate_experiments, get_experiments_list
from mrunner.utils.neptune import NeptuneWrapperCmd#, NeptuneToken, NEPTUNE_LOCAL_VERSION

LOGGER = logging.getLogger(__name__)


def get_default_config_path(ctx):
    default_config_file_name = 'config.yaml'

    app_name = Path(ctx.command_path).stem
    app_dir = Path(click.get_app_dir(app_name))
    return app_dir / default_config_file_name


@click.group()
@click.option('--debug/--no-debug', default=False, help='Enable debug messages')
@click.option('--config', default=None, type=click.Path(dir_okay=False),
              help='Path to mrunner yaml configuration')
@click.option('--context', default=None, help='Name of remote context to use '
                                              '(if not provided, "contexts.current" conf key will be used)')
@click.pass_context
def cli(ctx, debug, config, context):
    """Deploy experiments on computation cluster"""

    log_tags_to_suppress = ['pykwalify', 'docker', 'kubernetes', 'paramiko', 'requests.packages']
    logging.basicConfig(level=debug and logging.DEBUG or logging.INFO)
    for tag in log_tags_to_suppress:
        logging.getLogger(tag).setLevel(logging.ERROR)

    # read configuration
    config_path = Path(config or get_default_config_path(ctx))
    LOGGER.debug('Using {} as mrunner config'.format(config_path))
    config = ConfigParser(config_path).load()

    cmd_require_context = ctx.invoked_subcommand not in ['context']
    if cmd_require_context:
        context_name = context or config.current_context or None
        if not context_name:
            raise click.ClickException(
                'Provide context name (use CLI "--context" option or use "mrunner context set-active" command)')
        if context_name not in config.contexts:
            raise click.ClickException(
                'Could not find predefined context: "{}". Use context add command.'.format(context_name))

        try:
            context = config.contexts[context_name]
            for k in ['neptune', 'storage_dir', 'backend_type', 'context_name']:
                if k not in context:
                    raise AttributeError('Missing required "{}" context key'.format(k))
        except KeyError:
            raise click.ClickException('Unknown context {}'.format(context_name))
        except AttributeError as e:
            raise click.ClickException(e)

    ctx.obj = {'config_path': config_path,
               'config': config,
               'context': context}


@cli.command()
@click.option('--neptune', type=click.Path(), help="Path to neptune experiment config")
@click.option('--spec', default='experiments_list', help="Name of function providing experiment specification")
@click.option('--tags', multiple=True, help='Additional tags')
@click.option('--requirements_file', type=click.Path(), help='Path to requirements file')
@click.option('--base_image', help='Base docker image used in experiment')
@click.argument('script')
@click.argument('params', nargs=-1)
@click.pass_context
def run(ctx, neptune, spec, tags, requirements_file, base_image, script, params):
    """Run experiment"""

    context = ctx.obj['context']

    # validate options and arguments
    requirements = requirements_file and [req.strip() for req in Path(requirements_file).open('r')] or []
    if context['backend_type'] == 'kubernetes' and not base_image:
        raise click.ClickException('Provide docker base image')
    if context['backend_type'] == 'kubernetes' and not requirements_file:
        raise click.ClickException('Provide requirements.txt file')

    neptune_dir = None
    try:
        # prepare neptune directory in case if neptune yamls shall be generated
        # if neptune_support and not neptune:
        # TODO(pm):refactor me please
        if True:
            script_path = Path(script)
            neptune_dir = script_path.parent / 'neptune_{}'.format(script_path.stem)
            neptune_dir.makedirs_p()

        for neptune_path, experiment in generate_experiments(script, neptune, context, spec=spec,
                                                             neptune_dir=neptune_dir):

            experiment.update({'base_image': base_image, 'requirements': requirements})

            # TODO(pm):remove me please
            neptune_support = True
            if neptune_support:
                script = experiment.pop('script')
                cmd = ' '.join([script] + list(params))
                # tags from neptune.yaml will be extracted by neptune
                additional_tags = context.get('tags', []) + list(tags)

                remote_neptune_token = None
                # if NEPTUNE_LOCAL_VERSION.version[0] == 2:
                #     experiment['local_neptune_token'] = NeptuneToken()
                #     assert experiment['local_neptune_token'].path.expanduser().exists(), \
                #         'Login to neptune first with `neptune account login` command'
                #
                #     remote_neptune_token = {
                #         'kubernetes': NeptuneToken,
                #         'slurm': lambda: SlurmNeptuneToken(experiment)
                #     }[experiment['backend_type']]()

                neptune_profile_name = remote_neptune_token.profile_name if remote_neptune_token else None
                experiment['cmd'] = NeptuneWrapperCmd(cmd=cmd, experiment_config_path=neptune_path,
                                                      neptune_storage=context['storage_dir'],
                                                      paths_to_dump=None,
                                                      additional_tags=additional_tags,
                                                      neptune_profile=neptune_profile_name)
                experiment.setdefault('paths_to_copy', [])
            else:
                # TODO: implement no neptune version
                # TODO: for sbatch set log path into something like os.path.join(resource_dir_path, "job_logs.txt")
                raise click.ClickException('Not implemented yet')

            run_kwargs = {'experiment': experiment}
            backend = {
                'kubernetes': KubernetesBackend,
                'slurm': SlurmBackend
            }[experiment['backend_type']]()
            # TODO: add calling experiments in parallel
            backend.run(**run_kwargs)
    finally:
        if neptune_dir:
            neptune_dir.rmtree_p()


cli.add_command(context_cli)

if __name__ == '__main__':
    cli()
