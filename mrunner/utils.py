import errno
import os
import random
import string


def mkdir_p(path):
    try:
        os.makedirs(path)
        return path
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            return path
        else:
            raise


def id_generator(n=10):
   return ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(n))