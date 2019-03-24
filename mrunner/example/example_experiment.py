
# ===============This code should be factored out ===========
import argparse
import os

import socket
from munch import Munch

import yaml


def is_neptune_online():
  # I wouldn't be suprised if this would depend on neptune version
  return 'NEPTUNE_ONLINE_CONTEXT' in os.environ


neptune_logger_on = False


def _ensure_compund_type(input):
  if type(input) is not str:
    return input

  try:
    input = eval(input, {})
    if type(input) is tuple or type(input) is list:
      return input
    else:
      return input
  except:
    return input

def get_configuration(print_diagnostics=False, with_neptune=False):
  global neptune_logger_on
  if is_neptune_online():
    #TODO: This is to be removed
    from deepsense import neptune
    _ctx = neptune.Context()
    exp_dir_path = os.getcwd()
    params = {k: _ensure_compund_type(_ctx.params[k]) for k in _ctx.params}
    _ctx.properties['pwd'] = os.getcwd()
    _ctx.properties['host'] = socket.gethostname()
  else:
    # local run
    parser = argparse.ArgumentParser(description='Debug run.')
    parser.add_argument('--ex', type=str, default="")
    parser.add_argument('--config', type=str, default="")
    parser.add_argument("--exp_dir_path", default="")
    commandline_args = parser.parse_args()
    exp_dir_path = commandline_args.exp_dir_path
    params = {}
    if commandline_args.ex:
      from path import Path
      vars = {'script': str(Path(commandline_args.ex).name)}
      exec(open(commandline_args.ex).read(), vars)
      spec_func = vars['spec']
      experiment = spec_func()[0] #take just the first experiment for testing
      params = experiment.parameters

    if commandline_args.config:
      print("File to load:{}".format(commandline_args.config))
      with open(commandline_args.config, "r") as f:
        params = yaml.load(f)
      if with_neptune:
        # install with  pip install neptune-client
        neptune_logger_on = True
        import neptune
        #TODO pass api_token otherwise!!!!!
        neptune.init(api_token='eyJhcGlfYWRkcmVzcyI6Imh0dHBzOi8vdWkubmVwdHVuZS5tbCIsImFwaV9rZXkiOiIwNDY5NmQzMi00ZjM4LTRhZTYtYjA3OS03MTQzOGM2MzQyM2YifQ==',
                     project_qualified_name='loss/sandbox')
        neptune.create_experiment()
        #TODO: push parameters to neptune


  if print_diagnostics:
    print("PYTHONPATH:{}".format(os.environ['PYTHONPATH']))
    print("cd {}".format(os.getcwd()))
    print(socket.gethostname())
    print("Params:{}".format(params))

  return Munch(params), exp_dir_path


def logger(m, v):
  global neptune_logger_on

  if neptune_logger_on:
    import neptune
    neptune.send_metric(m, v)
  else:
    print("{}:{}".format(m, v))

# ===============^^This code should be factored out ===========

# install pip install neptune-client
# To run locally: mrunner/example/example_experiment.py --ex mrunner/example/example_experiment_conf.py
#
def main():
  #@HM: Here you can check MPI_RANK and set with_neptune=True/False
  config, exp_dir_path = get_configuration(print_diagnostics=True,
                                           with_neptune=True)
  for x in range(10):
    logger("test channel", x)


if __name__ == '__main__':
  main()