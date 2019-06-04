# Minimal mrunner experiment configuration
from munch import Munch

from mrunner.experiment import Experiment
import os

if "NEPTUNE_API_TOKEN" not in os.environ or "PROJECT_QUALIFIED_NAME" not in os.environ:
    print("Please set NEPTUNE_API_TOKEN and PROJECT_QUALIFIED_NAME env variables")
    print("Their values can be from up.neptune.ml. Click help and then quickstart.")
    exit(1)

exp = Experiment(name='Basic experiment',
                 script='python experiment_basic.py',
                 project=os.environ["PROJECT_QUALIFIED_NAME"],
                 tags=['test_experiments'],
                 env={"NEPTUNE_API_TOKEN": os.environ["NEPTUNE_API_TOKEN"]},
                 python_path='.', paths_to_dump='',
                 parameters=Munch(param1=10),
                 time='0-0:10')

# Only one experiment here
spec = [exp]
