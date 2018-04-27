# -*- coding: utf-8 -*-

import click
import six
import yaml

from mrunner.utils import DObject


class Config(DObject):
    _RESERVED = ['contexts']

    def set(self, key, value):
        from copy import copy

        if any([key.startswith(rkey) for rkey in self._RESERVED]):
            raise ValueError('Config key: "{}" is reserved'.format(key))

        parts = key.split('.')
        rparts = copy(parts)
        rparts.reverse()

        d = self
        while len(rparts) > 1:
            k = rparts.pop()
            d[k] = d.get(k, {})
            d = d[k]
            if not isinstance(d, dict):
                till_now_key = '.'.join(parts[:len(parts) - len(rparts)])
                raise ValueError('Key "{}" already set'.format(till_now_key))
        d[rparts[0]] = value

    def unset(self, key):
        from copy import copy
        if any([key.startswith(rkey) for rkey in self._RESERVED]):
            raise ValueError('Config key: "{}" is reserved'.format(key))

        parts = key.split('.')
        rparts = copy(parts)
        rparts.reverse()

        d = self
        while len(rparts) > 1:
            k = rparts.pop()
            d = d.get(k, None)

            till_now_key = '.'.join(parts[:len(parts) - len(rparts)])
            if d is None:
                raise ValueError('Key "{} is missing'.format(till_now_key))
        del d[rparts[0]]

    def __str__(self):
        lines = []

        def format_line(ks, v):
            lines.append('{}\t{}'.format('.'.join(ks), v))

        def _visit_tree(keys, value, format_func):
            key = '.'.join(keys)
            if key not in self._RESERVED:
                if isinstance(value, dict):
                    for k, v in value.items():
                        _visit_tree(keys + [k, ], v, format_func)
                else:
                    format_func(keys, value)

        for k, v in self.items():
            _visit_tree([k, ], v, format_line)
        return '\n'.join(lines)


class ConfigParser(object):

    def __init__(self, file_path):
        self._config_path = file_path

    def load(self):
        config = Config()
        if self._config_path.exists():
            with self._config_path.open('r') as conf_file:
                config = Config(**yaml.load(conf_file) or {})
        return config

    def save(self, config):
        from six import StringIO

        # first dump config to memory
        output = StringIO()
        yaml.safe_dump(config.to_dict(), output, default_flow_style=False)
        yaml_payload = six.u(output.getvalue())

        # then save to file
        self._config_path.parent.makedirs_p()
        with self._config_path.open('w') as config_file:
            config_file.write(yaml_payload)


class Context(DObject):
    pass


@click.group(invoke_without_command=True)
@click.pass_context
def config(ctx):
    """Manage application config"""
    if not ctx.invoked_subcommand:
        config = Config(**ctx.obj['config'])
        click.echo(config)


@config.command(name='set')
@click.argument('key')
@click.argument('value')
@click.pass_context
def config_set(ctx, key, value):
    """Set config key"""
    config = Config(**ctx.obj['config'])
    config_path = ctx.obj['config_path']

    try:
        config.set(str(key), str(value))
    except ValueError as e:
        raise click.ClickException(e.message)
    ConfigParser(config_path).save(config)


@config.command(name='unset')
@click.argument('key')
@click.pass_context
def config_unset(ctx, key):
    """Unset config key"""
    config = Config(**ctx.obj['config'])
    config_path = ctx.obj['config_path']

    try:
        config.unset(str(key))
    except ValueError as e:
        raise click.ClickException(e.message)
    ConfigParser(config_path).save(config)


@click.group(invoke_without_command=True)
@click.pass_context
def context(ctx):
    """manage remote context's"""
    if not ctx.invoked_subcommand:
        config = Config(**ctx.obj['config'])
        current_context = ctx.obj['context']
        for context_name in config.contexts:
            active = current_context and context_name == current_context.name
            click.echo('{}{}'.format(context_name, active and '\t(active)' or ''))


# TODO: [PZ] copy help from t2t
@context.command(name='add')
@click.option('--name', required=True, help='remote context name')
@click.option('--type', required=True,
              type=click.Choice(['kubernetes', 'slurm']), help='type of context')
@click.option('--storage', default=None, help='storage path to which neptune will copy source code')
@click.option('--resources', default=None, help='resources list to request')
@click.option('--registry_url', default=None, help='url to docker container\'s registry')
@click.option('--neptune/--no-neptune', default=True, help='use neptune')
@click.pass_context
def context_add(ctx, name, type, storage, resources, registry_url, neptune):
    """add new context"""
    config = Config(**ctx.obj['config'])
    config_path = ctx.obj['config_path']

    context = {'name': name, 'type': type, 'neptune': neptune, 'storage': storage, 'registry_url': registry_url,
               'resources': resources}
    context = Context(**{k: v for k, v in context.items() if v})
    try:
        if name in config.contexts:
            raise ValueError('Context "{}" already exists'.format(name))
        config.contexts[name] = context
    except ValueError as e:
        raise click.ClickException(e.message)
    ConfigParser(config_path).save(config)


@context.command(name='edit')
@click.argument('name')
@click.pass_context
def context_edit(ctx, name):
    """edit context"""
    from six import StringIO

    config = Config(**ctx.obj['config'])
    config_path = ctx.obj['config_path']

    try:
        if name not in config.contexts:
            raise ValueError('Context "{}" is missing'.format(name))

        context = config.contexts[name]
        text = yaml.safe_dump(context.to_dict(), default_flow_style=False)

        updated_text = click.edit(text)
        if updated_text:
            updated_context = updated_text and Context(**yaml.load(StringIO(updated_text))) or context

            if updated_context.name != context.name:
                del config.contexts[context.name]
                if config.current_context == context.name:
                    config.set('current_context', updated_context.name)

            config.contexts[updated_context.name] = updated_context
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
    config = Config(**ctx.obj['config'])
    config_path = ctx.obj['config_path']

    try:
        if name not in config.contexts:
            raise ValueError('Context "{}" is missing'.format(name))
        del config.contexts[name]
    except ValueError as e:
        raise click.ClickException(e.message)
    ConfigParser(config_path).save(config)
