# TODO(pm): move this to be importable from mrunner


import argparse
import os
import socket
from munch import Munch
import cloudpickle
neptune_logger_on = False



def nest_params(params, prefixes):
  """Nest params based od keys prefixes.

  Example:
    For input
    params = dict(
      param0=value0,
      prefix0_param1=value1,
      prefix0_param2=value2
    )
    prefixes = ("prefix0_",)
    This method modifies params into nested dictionary:
    {
      "param0" : value0
      "prefix0": {
        "param1": value1,
        "param2": value2
      }
    }
  """
  for prefix in prefixes:
    dict_params = Munch()
    l = len(prefix)
    for k in list(params.keys()):
      if k.startswith(prefix):
        dict_params[k[l:]] = params.pop(k)
    params[prefix[:-1]] = dict_params


def neptune_set_property(key, value):
  """Set property, cast value to str if needed

  Note that neptune.set_property() might raise exception but also can
  fail silently.
  """
  import neptune
  def set_property_assert_value(key, value):
    neptune.set_property(key, value)
    assert neptune.get_experiment().get_properties()[key] == value

  try:
    set_property_assert_value(key, value)
  except:
    try:
      set_property_assert_value(key, str(value))
    except:
      neptune.set_property(
        name, "Not possible to send to neptune. Implement __str__"
      )


def get_configuration(
        print_diagnostics=False, with_neptune=False,
        inject_parameters_to_gin=False, nesting_prefixes=()
):
  global neptune_logger_on

  parser = argparse.ArgumentParser(description='Debug run.')
  parser.add_argument('--ex', type=str, default="")
  parser.add_argument('--config', type=str, default="")
  commandline_args = parser.parse_args()

  params = None
  experiment = None
  spec_filename = None

  if commandline_args.ex:
    from path import Path
    spec_filename = str(Path(commandline_args.ex).name)
    vars = {'script': spec_filename}  # Do we need it?
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
      neptune.create_experiment(name=experiment.name, tags=experiment.tags)
      for name in params:
        neptune_set_property(name, params[name])

      # Set pwd property with path to experiment.
      neptune_set_property("pwd", os.getcwd())
      # Add specification filename to tags if present (might be added e.g by
      # mrunner or --ex parameter in local run without mrunner)
      if "script" in globals():
        spec_filename = globals()["script"]
      if spec_filename:
        neptune.get_experiment().append_tag(
          spec_filename[:-3]  # remove ".py"
        )
      import atexit
      atexit.register(neptune.stop)

  # TODO(pm): find a way to pass metainformation
  if print_diagnostics:
    print("PYTHONPATH:{}".format(os.environ.get('PYTHONPATH', 'not_defined')))
    print("cd {}".format(os.getcwd()))
    print(socket.getfqdn())
    print("Params:{}".format(params))

  nest_params(params, nesting_prefixes)

  return params


def logger(m, v):
  global neptune_logger_on

  if neptune_logger_on:
    import neptune
    neptune.send_metric(m, v)
  else:
    print("{}:{}".format(m, v))
