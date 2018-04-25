# -*- coding: utf-8 -*-
from copy import deepcopy

import attr
import click
import six
import yaml

Config = attr.make_class('Config', ['contexts', 'current_context'])


class ConfigParser(object):

    def __init__(self, file_path):
        self._config_path = file_path

    def load(self):
        config = {}
        if self._config_path.exists():
            with self._config_path.open('r') as conf_file:
                config = Config(**yaml.load(conf_file) or {})
        return config

    def save(self, config):
        from six import StringIO

        # first dump config to memory
        output = StringIO()
        yaml.safe_dump(attr.asdict(config), output, default_flow_style=False)
        yaml_payload = six.u(output.getvalue())

        # then save to file
        self._config_path.parent.makedirs_p()
        with self._config_path.open('w') as config_file:
            config_file.write(yaml_payload)


@click.group(invoke_without_command=True)
@click.pass_context
def context(ctx):
    """manage remote context's"""
    if not ctx.invoked_subcommand:
        config = ctx.obj['config']
        current_context = ctx.obj['context']
        for context_name in config.contexts:
            active = current_context and context_name == current_context['context_name']
            click.echo('{}{}'.format(context_name, active and '\t(active)' or ''))


@context.command(name='add')
@click.option('--name', required=True, help='remote context name')
@click.option('--backend_type', required=True,
              type=click.Choice(['kubernetes', 'slurm']), help='type of backend')
@click.option('--storage', default=None, help='storage path to which neptune will copy source code')
@click.option('--resources', default=None, multiple=True, help='resources list to request (ex. cpu=1 mem=2G)')
@click.option('--registry_url', default=None, help='url to docker container\'s registry')
@click.option('--neptune/--no-neptune', default=True, help='use neptune')
@click.pass_context
def context_add(ctx, name, backend_type, storage, resources, registry_url, neptune):
    """add new context"""
    config = ctx.obj['config']
    config_path = ctx.obj['config_path']

    context = {'context_name': name, 'backend_type': backend_type, 'neptune': neptune, 'storage_dir': storage,
               'registry_url': registry_url, 'resources': dict([r.split('=') for r in resources])}
    context = {k: v for k, v in context.items() if v}
    try:
        if name in config.contexts:
            raise ValueError('Context "{}" already exists'.format(name))
        config.contexts[name] = context
    except ValueError as e:
        raise click.ClickException(e)
    ConfigParser(config_path).save(config)


@context.command(name='edit')
@click.argument('name')
@click.pass_context
def context_edit(ctx, name):
    """edit context"""
    from six import StringIO

    config = ctx.obj['config']
    config_path = ctx.obj['config_path']

    try:
        if name not in config.contexts:
            raise ValueError('Context "{}" is missing'.format(name))

        context = config.contexts[name]
        text = yaml.safe_dump(context, default_flow_style=False)

        updated_text = click.edit(text)
        if updated_text:
            updated_context = updated_text and yaml.load(StringIO(updated_text)) or context

            if updated_context['context_name'] != context['context_name']:
                del config.contexts[context['context_name']]
                if config.current_context == context['context_name']:
                    config.set('current_context', updated_context['context_name'])

            config.contexts[updated_context['context_name']] = updated_context
        else:
            click.echo('No changes in context')
    except ValueError as e:
        raise click.ClickException(e)
    except yaml.parser.ParserError as e:
        raise click.ClickException('Could not parser YAML')
    ConfigParser(config_path).save(config)


@context.command(name='delete')
@click.argument("name")
@click.pass_context
def context_delete(ctx, name):
    """delete context"""
    config = ctx.obj['config']
    config_path = ctx.obj['config_path']

    try:
        if name not in config.contexts:
            raise ValueError('Context "{}" is missing'.format(name))
        del config.contexts[name]
    except ValueError as e:
        raise click.ClickException(e)
    ConfigParser(config_path).save(config)


@context.command(name='set-active')
@click.argument("name")
@click.pass_context
def context_set_active(ctx, name):
    """delete context"""
    config = ctx.obj['config']
    config_path = ctx.obj['config_path']

    try:
        if name not in config.contexts:
            raise ValueError('Context "{}" is missing'.format(name))
        config.current_context = name
    except ValueError as e:
        raise click.ClickException(e)
    ConfigParser(config_path).save(config)


@context.command(name='copy')
@click.argument("src")
@click.argument("dst")
@click.pass_context
def context_copy(ctx, src, dst):
    """delete context"""
    config = ctx.obj['config']
    config_path = ctx.obj['config_path']

    try:
        if src not in config.contexts:
            raise ValueError('Context "{}" is missing'.format(src))
        if dst in config.contexts:
            raise ValueError('Context "{}" already set (delete it first)'.format(dst))
        config.contexts[dst] = deepcopy(config.contexts[src])
    except ValueError as e:
        raise click.ClickException(e)
    ConfigParser(config_path).save(config)
