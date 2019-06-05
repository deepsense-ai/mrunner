from mrunner.helpers.client_helper import get_configuration, logger
import gin

@gin.configurable
class LinearFunction:

  def __init__(self, coefficient):
    self.coefficient = coefficient

  def __call__(self, *args, **kwargs):
    return self.coefficient*args[0]


def main():
  params = get_configuration(print_diagnostics=True, with_neptune=True,
                             inject_parameters_to_gin=True)
  lin_fun = LinearFunction()

  for x in range(params.param1):
    logger("test channel1", lin_fun(x))



if __name__ == '__main__':
  main()
