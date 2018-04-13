#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

import click
from path import Path

from mrunner.cmd import NeptuneWrapperCmd
from mrunner.config import ConfigParser, config, context
from mrunner.docker_engine import DockerEngine
from mrunner.experiment import Experiment
from mrunner.k8s import KubernetesBackend
from mrunner.neptune import load_neptune_config


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

    logging.basicConfig(level=debug and logging.DEBUG or logging.INFO)

    # read configuration
    config_path = get_default_config_path(ctx)
    config = ConfigParser(config_path).load()

    context_name = context or config.current_context or None
    cmd_require_context = ctx.invoked_subcommand not in ['config', 'context']
    if cmd_require_context and not context_name:
        raise click.ClickException('Provide context name (use option or set "contexts.current" config key)')
    if cmd_require_context and context_name not in config.contexts:
        raise click.ClickException('Could not find predefined context: "{}"'.format(context_name))

    ctx.obj = {'config_path': config_path,
               'config': config,
               'context': config.contexts.get(context_name, None)}


@cli.command()
@click.option('--config', required=True, type=click.Path(), help="Path to neptune experiment config")
@click.option('--tag', multiple=True, help='Additional tag')
@click.option('--requirements', type=click.Path(), help='Path to requirements file')
@click.option('--base_image', help='Base docker image used in experiment')
@click.argument('script')
@click.argument('params', nargs=-1)
@click.pass_context
def run(ctx, config, tag, requirements, base_image, script, params):
    """Run experiment"""

    context = ctx.obj['context']

    if context.neptune:
        cmd = ' '.join([script] + list(params))
        # tags from neptune.yaml will be extracted by neptune
        additional_tags = (context.tags or []) + list(tag)
        cmd = NeptuneWrapperCmd(cmd=cmd, experiment_config_path=config,
                                neptune_storage=context.storage,
                                paths_to_dump=None,
                                additional_tags=additional_tags)
    else:
        raise click.ClickException('Not implemented yet')

    requirements = requirements and [req.strip() for req in Path(requirements).open('r')] or []
    if context.type == 'kubernetes' and not base_image:
        raise click.ClickException('Provide docker base image')

    neptune_config = load_neptune_config(config)
    experiment = Experiment(
        project_name=neptune_config.project,
        name=neptune_config.name.lower().replace(' ', '-'),
        base_image=base_image,
        requirements=requirements,
        cmd=cmd,
        paths_to_copy=neptune_config.paths_to_copy,
        exclude=neptune_config.exclude,
        cwd=Path.getcwd()
    )
    image_name = DockerEngine(context=context).build_and_publish_image(experiment=experiment)
    KubernetesBackend(context=context).run(image=image_name, experiment=experiment)


cli.add_command(config)
cli.add_command(context)

if __name__ == '__main__':
    cli()
