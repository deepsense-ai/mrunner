import datetime
import errno
import os
import random
import string
from tempfile import NamedTemporaryFile

from addict import Dict
from jinja2 import Environment, PackageLoader, StrictUndefined


def mkdir_p(path):
    try:
        os.makedirs(path)
        return path
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            return path
        else:
            raise


def id_generator(n=10):
    return ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(n))


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
        return self._file.name


class GeneratedTemplateFile(TempFile):

    def __init__(self, template_filename=None, **kwargs):
        super(GeneratedTemplateFile, self).__init__()
        template = template_env.get_template(template_filename)
        payload = template.render(**kwargs).encode(encoding='utf-8')
        self.write(payload)


class DObject(Dict):

    def __setattr__(self, name, value):
        raise AttributeError('{} object is immutable'.format(self.__class__.__name__))

    def to_dict(self):

        base = {}
        for key, value in self.items():
            # This method was required, because original function doesn't convert recursively whole object
            # TODO: investigate why value is class Dict not child of DObject (ex. Config)
            # print(key, value, value.__class__, type(class)
            if isinstance(value, Dict):
                base[key] = value.to_dict()
            elif isinstance(value, (list, tuple)):
                base[key] = type(value)(
                    item.to_dict() if isinstance(item, type(self)) else
                    item for item in value)
            else:
                base[key] = value
        return base

    @classmethod
    def _hook(cls, item):
        if isinstance(item, Dict):
            return item
        return Dict._hook(item)
