import os
from collections import Mapping, OrderedDict
from itertools import product
from typing import List

from munch import Munch
from neptune.utils import get_git_info

from mrunner.experiment import Experiment
from mrunner.utils.namesgenerator import get_random_name
import copy
import pathlib


def create_experiments_helper(experiment_name: str, base_config: dict,
                              project_name:str, params_grid,
                              script: str, python_path: str,
                              paths_to_dump: str, tags: List[str], add_random_tag=True,
                              exclude_git_files=True,
                              exclude=[], with_neptune=True,
                              update_lambda=lambda d1, d2: d1.update(d2),
                              callbacks=[]):

  _script_name = globals()['script']
  _script_name = None if _script_name is None else pathlib.Path(_script_name).stem
  if _script_name:
    tags.append(_script_name)
  if add_random_tag:
    random_tag = get_random_name()
    tags.append(random_tag)

  env = {}
  if with_neptune:
      if "NEPTUNE_API_TOKEN" in os.environ:
          env = {"NEPTUNE_API_TOKEN": os.environ["NEPTUNE_API_TOKEN"]}
      else:
          print("NEPTUNE_API_TOKEN is not set. Connecting with neptune will fail.")

  params_configurations = get_combinations(params_grid)
  experiments = []

  git_info = None
  if exclude_git_files:
    exclude += [".git"]
    git_info = get_git_info(".")
    if git_info:
      # Hack due to external bugs
      git_info.commit_date = None

  #Last chance to change something
  for callback in callbacks:
      callback(**locals())

  for params_configuration in params_configurations:
    config = copy.deepcopy(base_config)
    update_lambda(config, params_configuration)
    config = Munch(config)


    experiments.append(Experiment(project=project_name, name=experiment_name, script=script,
                                  parameters=config, python_path=python_path,
                                  paths_to_dump=paths_to_dump, tags=tags, env=env,
                                  exclude=exclude, git_info=git_info))

  return experiments


def get_container_types():
  ret = [list, tuple]
  try:
    import numpy as np
    ret.append(np.ndarray)
  except ImportError:
    pass
  try:
    import pandas as pd
    ret.append(pd.Series)
  except ImportError:
    pass
  return tuple(ret)

#TODO(pm): refactor me please
def get_combinations(param_grids, limit=None):
  """
  Based on sklearn code for grid search. Get all hparams combinations based on
  grid(s).
  :param param_grids: dict representing hparams grid, or list of such
  mappings
  :returns: list of OrderedDict (if params_grids consisted OrderedDicts,
   the Order of parameters will be sustained.)
  """
  allowed_container_types = get_container_types()
  if isinstance(param_grids, Mapping):
    # Wrap dictionary in a singleton list to support either dict or list of
    # dicts.
    param_grids = [param_grids]

  combinations = []
  for param_grid in param_grids:
    items = param_grid.items()
    if not items:
      combinations.append(OrderedDict())
    else:
      keys___ = []
      grids___ = []
      keys = []
      grids = []

      for key, grid in items:
        if '___' in key:
          keys___.append(key[:-3])
          grids___.append(grid)
        else:
          keys.append(key)
          grids.append(grid)

      for grid in grids+grids___:
        assert isinstance(grid, allowed_container_types), \
          'grid values should be passed in one of given types: {}, got {} ({})' \
            .format(allowed_container_types, type(grid), grid)

      if grids___:
        for param_values___ in zip(*grids___):
          for param_values in product(*grids):
            combination = OrderedDict(zip(keys___+keys, param_values___+param_values))
            combinations.append(combination)
      else:
        for param_values in product(*grids):
          combination = OrderedDict(zip( keys, param_values))
          combinations.append(combination)

  if limit:
    combinations = combinations[:limit]
  return combinations