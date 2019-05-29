from munch import Munch
from mrunner.experiment import Experiment

def create_experiment_for_spec(parameters):
   script = 'python example_experiment.py'

   name = 'Piotr Milos test experiment'

   project_name = 'loss/sandbox'
   python_path = '.:some_utils:some/other/utils/path'

   paths_to_dump = ''

   tags = ['test_experiments']

   return Experiment(project=project_name, name=name, script=script,
                     parameters=parameters, python_path=python_path,
                     paths_to_dump=paths_to_dump, tags=tags,
                     time='0-0:10'
                     )



def spec():
  params = Munch(param1=10, param2=12)
  experiments = [create_experiment_for_spec(params)]
  return experiments
