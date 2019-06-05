from mrunner.helpers.client_helper import get_configuration, logger
import numpy as np
from mpi4py import MPI as mpi


def main():

  rank = mpi.COMM_WORLD.Get_rank()
  if rank == 0:
    config = get_configuration(print_diagnostics=True, with_neptune=True)
  else:
    config = get_configuration(print_diagnostics=True, with_neptune=False)


  for x in range(10):
    gather_res = mpi.COMM_WORLD.gather(x + config.param1, root=0)
    if rank == 0:
      logger("test channel", np.sum(gather_res))

  mpi.COMM_WORLD.Barrier()


if __name__ == '__main__':
  main()
