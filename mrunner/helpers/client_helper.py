import argparse
import datetime
import os
import socket
from munch import Munch
import cloudpickle
import ast
import logging

experiment_ = None
logger_ = logging.getLogger(__name__)


def inject_dict_to_gin(dict, scope=None):
    import gin
    bindings = []
    scope_str = "" if scope is None else f"{scope}/"
    for key, value in dict.items():
        if type(value) is str and value[0] == "@":
            # value = '"' + value + '"' if type(value) is str else value
            bindings.append(f"{scope_str}{key} = {value}")
        else:
            gin.bind_parameter(key, value)
    gin.parse_config(bindings)


def nest_params(params, prefixes):
    """Nest params based on keys prefixes.

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
        l_ = len(prefix)
        for k in list(params.keys()):
            if k.startswith(prefix):
                dict_params[k[l_:]] = params.pop(k)
        params[prefix[:-1]] = dict_params


def get_configuration(
        print_diagnostics=False, with_neptune=False,
        inject_parameters_to_gin=False, nesting_prefixes=()
):
    # with_neptune might be also an id of an experiment
    global experiment_

    parser = argparse.ArgumentParser(description='Debug run.')
    parser.add_argument('--ex', type=str, default="")
    parser.add_argument('--config', type=str, default="")
    commandline_args = parser.parse_args()

    params = None
    experiment = None
    git_info = None

    # This is here for running locally, load experiment from spec
    if commandline_args.ex:
        from path import Path
        vars_ = {'script': str(Path(commandline_args.ex).name)}
        exec(open(commandline_args.ex).read(), vars_)
        experiments = vars_['experiments_list']
        logger_.info("The specifcation file contains {} "
                     "experiments configurations. The first one will be used.".format(len(experiments)))
        experiment = experiments[0]
        params = experiment.parameters

    # This is here for running remotely, load experiment from dump
    if commandline_args.config:
        logger_.info("File to load:{}".format(commandline_args.config))
        with open(commandline_args.config, "rb") as f:
            experiment = Munch(cloudpickle.load(f))
        params = Munch(experiment['parameters'])
        git_info = experiment.get("git_info", None)
        if git_info:
            git_info.commit_date = datetime.datetime.now()

    if inject_parameters_to_gin:
        logger_.info("The parameters of the form 'aaa.bbb' will be injected to gin.")
        gin_params = {param_name:params[param_name] for param_name in params if "." in param_name}
        inject_dict_to_gin(gin_params)

    if with_neptune == True:
        if 'NEPTUNE_API_TOKEN' not in os.environ:
            logger_.warn("Neptune will be not used.\nTo run with neptune please set your NEPTUNE_API_TOKEN variable")
        else:
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
                   logger_.warn("Not possible to send to neptune:{}. Implement __str__".format(param_name))

            # Set pwd property with path to experiment.
            properties = {"pwd": os.getcwd()}
            neptune.create_experiment(name=experiment.name, tags=experiment.tags,
                                      params=params, properties=properties,
                                      git_info=git_info)

            import atexit
            atexit.register(neptune.stop)
            experiment_ = neptune.get_experiment()

    if type(with_neptune) == str:
        import neptune
        logger_.info("Connecting to experiment:", with_neptune)
        print_diagnostics = False
        neptune.init(project_qualified_name=experiment.project)
        experiment_ = neptune.project.get_experiments(with_neptune)[0]

    if print_diagnostics:
        logger_.info("PYTHONPATH:{}".format(os.environ.get('PYTHONPATH', 'not_defined')))
        logger_.info("cd {}".format(os.getcwd()))
        logger_.info(socket.getfqdn())
        logger_.info("Params:{}".format(params))

    nest_params(params, nesting_prefixes)
    if experiment_:
        params['experiment_id'] = experiment_.id
    else:
        params['experiment_id'] = None

    return params


def logger(m, v):
    global experiment_

    if experiment_:
        import neptune
        from PIL import Image
        m = m.lstrip().rstrip()  # This is to circumvent neptune's bug
        if type(v) == Image.Image:
            experiment_.send_image(m, v)
        else:
            experiment_.send_metric(m, v)
    else:
        print("{}:{}".format(m, v))
