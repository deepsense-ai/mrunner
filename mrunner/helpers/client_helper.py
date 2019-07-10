# TODO(pm): move this to be importable from mrunner


import argparse
import os
import socket
from munch import Munch
import cloudpickle
neptune_logger_on = False
import ast


def get_configuration(print_diagnostics=False, with_neptune=False, inject_parameters_to_gin=False):
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
    experiments = vars['experiments_list']
    print("The specifcation file contains {} "
          "experiments configurations. The first one will be used.".format(len(experiments)))
    experiment = experiments[0]
    params = experiment.parameters

  # TODO(pm): why not make mrunner to pickle experiment so that we do not have to homogenize here
  if commandline_args.config:
    print("File to load:{}".format(commandline_args.config))
    with open(commandline_args.config, "rb") as f:
      experiment = Munch(cloudpickle.load(f))
    params = Munch(experiment['parameters'])

  if inject_parameters_to_gin:
    print("The parameters of the form 'aaa.bbb' will be injected to gin.")
    import gin
    import gin.tf.external_configurables
    for param_name in params:
      if "." in param_name:
        gin.bind_parameter(param_name, params[param_name])


  if with_neptune:
    if 'NEPTUNE_API_TOKEN' not in os.environ:
      print("Neptune will be not used.\nTo run with neptune please set your NEPTUNE_API_TOKEN variable")
    else:
      neptune_logger_on = True
      import neptune
      neptune.init(project_qualified_name=experiment.project)
      params_to_sent_to_neptune = {}
      for param_name in params:
        try:
          val = str(params[param_name])
          if val.isnumeric():
            val = ast.literal_eval(val)
          params_to_sent_to_neptune[param_name] = val
        except:
          print("Not possible to send to neptune:{}. Implement __str__".format(param_name))

      neptune.create_experiment(name=experiment.name, tags=experiment.tags, params=params)

      import atexit
      atexit.register(neptune.stop)


  # TODO(pm): find a way to pass metainformation
  if print_diagnostics:
    print("PYTHONPATH:{}".format(os.environ.get('PYTHONPATH', 'not_defined')))
    print("cd {}".format(os.getcwd()))
    print(socket.getfqdn())
    print("Params:{}".format(params))

  return params


def logger(m, v):
  global neptune_logger_on

  if neptune_logger_on:
    import neptune
    neptune.send_metric(m, v)
  else:
    print("{}:{}".format(m, v))
