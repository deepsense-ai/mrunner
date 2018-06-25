import datetime
from collections import namedtuple, OrderedDict
from tempfile import NamedTemporaryFile

import attr
from jinja2 import Environment, PackageLoader, StrictUndefined
from path import Path

from mrunner.utils.namesgenerator import id_generator


def get_experiment_dirname():
    return datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S') + '_' + id_generator(4)


def parse_argv(parser, argv):
    try:
        divider_pos = argv.index('--')
        mrunner_argv = argv[1:divider_pos]
        rest_argv = argv[divider_pos + 1:]
    except ValueError:
        # when missing '--' separator
        mrunner_argv = argv
        rest_argv = []
    return parser.parse_args(args=mrunner_argv), rest_argv


template_env = Environment(
    loader=PackageLoader('mrunner', 'templates'),
    undefined=StrictUndefined
)


class TempFile(object):

    def __init__(self, dir=None):
        self._file = NamedTemporaryFile(prefix='mrunner_', dir=dir)

    def write(self, payload):
        self._file.write(payload)
        self._file.flush()

    @property
    def path(self):
        return Path(self._file.name)


class GeneratedTemplateFile(TempFile):

    def __init__(self, template_filename=None, **kwargs):
        super(GeneratedTemplateFile, self).__init__()
        template = template_env.get_template(template_filename)
        payload = template.render(**kwargs).encode(encoding='utf-8')
        self.write(payload)


PathToDump = namedtuple('PathToDump', 'local_path rel_remote_path')


def get_paths_to_copy(paths_to_copy=None, exclude=None):
    """Lists paths to copy from current working directory, after excluding paths from exclude list;
    additionally paths_to_copy are copied"""

    if paths_to_copy is None:
        paths_to_copy = []
    if exclude is None:
        exclude = []
    exclude = [Path(e).abspath() for e in exclude]

    def _list_dir(d):
        directories = []
        for p in Path(d).listdir():
            p = p.abspath()
            excluded = False
            for e in exclude:
                e = e.abspath()
                if not e.relpath(p).startswith('..'):
                    excluded = True
                    # if excluded subdir - not whole current
                    if e != p:
                        directories += _list_dir(p)
                    break
            if not excluded:
                directories.append(PathToDump(p.relpath('.'), p.relpath('.')))
        return directories

    result = _list_dir(Path('.'))
    for external in paths_to_copy:
        if ':' in external:
            src, rel_dst = external.split(':')
        else:
            src = external
            # get relative to cwd split into items on each '/' and remove relative parts
            rel_dst = '/'.join([item for item in Path(external).relpath('.').splitall() if item and item != '..'])
        result.append(PathToDump(Path(src).relpath('.'), Path(rel_dst).relpath('.')))
    return result


def make_attr_class(class_name, fields, **class_kwargs):
    fields = OrderedDict([(k, attr.ib(**kwargs) if isinstance(kwargs, dict) else kwargs) for k, kwargs in fields])
    return attr.make_class(class_name, fields, **class_kwargs)


def filter_only_attr(AttrClass, d):
    available_fields = [f.name for f in attr.fields(AttrClass)]
    return {k: v for k, v in d.items() if k in available_fields}
