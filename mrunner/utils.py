import datetime
import errno
import os
import random
import string


def mkdir_p(path):
    try:
        os.makedirs(path)
        return path
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            return path
        else:
            raise


def id_generator(n=10):
    return ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(n))


def get_experiment_dirname():
    return datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S') + '_' + id_generator(4)


def parse_argv(parser, argv):
    try:
        divider_pos = argv.index('--')
        mrunner_argv = argv[1:divider_pos]
        rest_argv = argv[divider_pos + 1:]
    except ValueError:
        # when missing '--' separator
        mrunner_argv = argv
        rest_argv = []
    return parser.parse_args(args=mrunner_argv), rest_argv
