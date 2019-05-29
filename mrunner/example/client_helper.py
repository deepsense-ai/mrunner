# TODO(pm): move this to be importable from mrunner


import argparse
import os
import socket
from munch import Munch
import yaml
neptune_logger_on = False


def get_configuration(print_diagnostics=False, with_neptune=False):
  global neptune_logger_on

  parser = argparse.ArgumentParser(description='Debug run.')
  parser.add_argument('--ex', type=str, default="")
  parser.add_argument('--config', type=str, default="")
  commandline_args = parser.parse_args()

  params = None
  experiment = None

  if commandline_args.ex:
    from path import Path
    vars = {'script': str(Path(commandline_args.ex).name)}
    exec(open(commandline_args.ex).read(), vars)
    spec_func = vars['spec']
    experiment = spec_func()[0] #take just the first experiment for testing
    params = experiment.parameters

  # TODO(pm): why not make mrunner to pickle experiment so that we do not have to homogenize here
  if commandline_args.config:
    print("File to load:{}".format(commandline_args.config))
    with open(commandline_args.config, "r") as f:
      experiment = Munch(yaml.load(f))
    params = Munch(experiment['parameters'])

  if with_neptune:
    neptune_logger_on = True
    import neptune
    #TODO pass api_token otherwise!!!!!
    neptune.init(api_token='eyJhcGlfYWRkcmVzcyI6Imh0dHBzOi8vdWkubmVwdHVuZS5tbCIsImFwaV9rZXkiOiIwNDY5NmQzMi00ZjM4LTRhZTYtYjA3OS03MTQzOGM2MzQyM2YifQ==',
                 project_qualified_name=experiment.project)
    neptune.create_experiment()

    #TODO: push parameters to neptune
    #TODO: add handle to quit experiment


  # TODO(pm): find a way to pass metainformation
  if print_diagnostics:
    print("PYTHONPATH:{}".format(os.environ.get('PYTHONPATH', 'not_defined')))
    print("cd {}".format(os.getcwd()))
    print(socket.gethostname())
    print("Params:{}".format(params))

  return params


def logger(m, v):
  global neptune_logger_on

  if neptune_logger_on:
    import neptune
    neptune.send_metric(m, v)
  else:
    print("{}:{}".format(m, v))
