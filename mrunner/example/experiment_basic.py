from mrunner.helpers.client_helper import get_configuration, logger


def main():
  params = get_configuration(print_diagnostics=True, with_neptune=True)
  for x in range(params.param1):
    logger("test channel", x)

  if "param3" in params:
    f = params["param3"] #or you can use params.param3
    for x in range(params.param1):
      logger("test channel", f(x))


if __name__ == '__main__':
  main()
