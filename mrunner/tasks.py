class LocalTask(object):
    def __init__(self, command, env):
        self.command = command
        self.env = env


class PlgridTask(object):
    def __init__(self, command, cwd=None, env={}, modules_to_load=[], venv_path=None):
        # paths_to_dump (dst_remote_path, local_path)
        self.command = command
        self.cwd = cwd
        self.env = env
        self.venv_path = venv_path
        self.modules_to_load = modules_to_load