# -*- coding: utf-8 -*-

import attr
from path import Path

from mrunner.utils import make_attr_class

COMMON_EXPERIMENT_MANDATORY_FIELDS = [
    ('backend_type', dict()),
    ('name', dict()),
    ('storage_dir', dict()),
    ('cmd', dict())
]

COMMON_EXPERIMENT_OPTIONAL_FIELDS = [
    ('project', dict(default='sandbox')),
    ('requirements', dict(default=attr.Factory(list), type=list)),
    ('exclude', dict(default=attr.Factory(list), type=list)),
    ('paths_to_copy', dict(default=attr.Factory(list), type=list)),
    ('env', dict(default=attr.Factory(dict), type=dict)),
    ('resources', dict(default=attr.Factory(dict), type=dict)),
    ('cwd', dict(default=attr.Factory(Path.getcwd))),
]

COMMON_EXPERIMENT_FIELDS = COMMON_EXPERIMENT_MANDATORY_FIELDS + COMMON_EXPERIMENT_OPTIONAL_FIELDS
Experiment2 = make_attr_class('Experiment2', COMMON_EXPERIMENT_FIELDS, frozen=True)
