#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re

import click
from path import Path

from mrunner.config import ConfigParser, context as context_cli
from mrunner.k8s import KubernetesBackend
from mrunner.neptune import load_neptune_config, NeptuneWrapperCmd
from mrunner.slurm import SlurmBackend

LOGGER = logging.getLogger(__name__)


def get_default_config_path(ctx):
    default_config_file_name = 'config.yaml'

    app_name = Path(ctx.command_path).stem
    app_dir = Path(click.get_app_dir(app_name))
    return app_dir / default_config_file_name


@click.group()
@click.option('--debug/--no-debug', default=False, help='Enable debug messages')
@click.option('--context', default=None, help='Name of remote context to use '
                                              '(if not provided, "contexts.current" conf key will be used)')
@click.pass_context
def cli(ctx, debug, context):
    """Deploy experiments on kubernetes cluster"""

    log_tags_to_suppress = ['pykwalify', 'docker', 'kubernetes', 'paramiko', 'requests.packages']
    logging.basicConfig(level=debug and logging.DEBUG or logging.INFO)
    for tag in log_tags_to_suppress:
        logging.getLogger(tag).setLevel(logging.ERROR)

    # read configuration
    config_path = get_default_config_path(ctx)
    config = ConfigParser(config_path).load()

    context_name = context or config.current_context or None
    cmd_require_context = ctx.invoked_subcommand not in ['config', 'context']
    if cmd_require_context and not context_name:
        raise click.ClickException('Provide context name (use option or set "contexts.current" config key)')
    if cmd_require_context and context_name not in config.contexts:
        raise click.ClickException('Could not find predefined context: "{}"'.format(context_name))

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


def merge_config(cli_kwargs, neptune_config, context):
    config = context.copy()
    for k, v in list(neptune_config.items()) + list(cli_kwargs.items()):
        if k not in config:
            LOGGER.debug('New config["{}"]: {}'.format(k, v))
            config[k] = v
        else:
            if isinstance(config[k], (list, tuple)):
                LOGGER.debug('Extending config["{}"]: {} with {}'.format(k, config[k], v))
                if isinstance(v, (list, tuple)):
                    config[k].extend(v)
                else:
                    config[k].append(v)
            else:
                LOGGER.debug('Overwriting config["{}"]: {} -> {}'.format(k, config[k], v))
                config[k] = v
    return config


@cli.command()
@click.option('--config', required=True, type=click.Path(), help="Path to neptune experiment config")
@click.option('--tags', multiple=True, help='Additional tags')
@click.option('--requirements_file', type=click.Path(), help='Path to requirements file')
@click.option('--base_image', help='Base docker image used in experiment')
@click.argument('script')
@click.argument('params', nargs=-1)
@click.pass_context
def run(ctx, config, tags, requirements_file, base_image, script, params):
    """Run experiment"""

    context = ctx.obj['context']

    if context['neptune']:
        cmd = ' '.join([script] + list(params))
        # tags from neptune.yaml will be extracted by neptune
        additional_tags = context.get('tags', []) + list(tags)
        cmd = NeptuneWrapperCmd(cmd=cmd, experiment_config_path=config,
                                neptune_storage=context['storage_dir'],
                                paths_to_dump=None,
                                additional_tags=additional_tags)
    else:
        # TODO: implement no neptune version
        # TODO: for sbatch set log path into something like os.path.join(resource_dir_path, "job_logs.txt")
        raise click.ClickException('Not implemented yet')

    requirements = requirements_file and [req.strip() for req in Path(requirements_file).open('r')] or []
    if context['backend_type'] == 'kubernetes' and not base_image:
        raise click.ClickException('Provide docker base image')
    if context['backend_type'] == 'kubernetes' and not requirements_file:
        raise click.ClickException('Provide requirements.txt file')

    neptune_config = load_neptune_config(config)
    del neptune_config['storage']
    cli_kwargs = {'config': config, 'tags': tags, 'requirements': requirements,
                  'base_image': base_image, 'cwd': Path.getcwd(), 'cmd': cmd,
                  'name': re.sub(r'[ .,_-]+', '-', neptune_config['name'].lower())}
    experiment = merge_config(cli_kwargs, neptune_config, context)

    run_kwargs = {'experiment': experiment}
    backend = {
        'kubernetes': KubernetesBackend,
        'slurm': SlurmBackend
    }[experiment['backend_type']]()
    backend.run(**run_kwargs)


cli.add_command(context_cli)

if __name__ == '__main__':
    cli()
