# Minimal mrunner experiment configuration
from munch import Munch

from mrunner.experiment import Experiment
import os

if "NEPTUNE_API_TOKEN" not in os.environ or "PROJECT_QUALIFIED_NAME" not in os.environ:
    print("Please set NEPTUNE_API_TOKEN and PROJECT_QUALIFIED_NAME env variables")
    print("Their values can be from up.neptune.ml. Click help and then quickstart.")
    exit()


def spec():
    script = 'python experiment_basic.py'

    name = 'experiment basic'

    project_name = os.environ["PROJECT_QUALIFIED_NAME"]
    python_path = '.'

    paths_to_dump = ''

    tags = ['test_experiments']

    env = {"NEPTUNE_API_TOKEN": os.environ["NEPTUNE_API_TOKEN"]}
    parameters = Munch(param1=10)

    exp = Experiment(project=project_name, name=name, script=script,
                     parameters=parameters, python_path=python_path,
                     paths_to_dump=paths_to_dump, tags=tags, env=env,
                     time='0-0:10')

    return [exp]
