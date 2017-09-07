class CommandWithEnv(object):
    def __init__(self, command, env):
        self.command = command
        self.env = env

    def generate_one_liner(self):
        raise NotImplementedError



class PlgridTask(object):
    def __init__(self, command, cwd=None, env={}, modules_to_load=[], venv_path=None,
                 after_module_load_cmd=None):
        # paths_to_dump (dst_remote_path, local_path)
        self.command = command
        self.cwd = cwd
        self.env = env
        self.venv_path = venv_path
        self.modules_to_load = modules_to_load
        self.after_module_load_cmd = after_module_load_cmd

    def construct_command(self):
        command = ''
        if self.cwd is not None:
            command += 'cd {cwd}\n'.format(cwd=self.cwd)

        command += 'module load test/pro-viz/1.0\n'
        command += 'module load plgrid/tools/ffmpeg/3.0\n'
        command += 'module load plgrid/tools/python/2.7.13\n'

        if self.after_module_load_cmd is not None:
            command += self.after_module_load_cmd + '\n'

        if self.venv_path is not None:
            command += 'source {venv_path}/bin/activate\n'.format(venv_path=self.venv_path)

        for name, val in self.env.iteritems():
            command += 'export {name}={val}\n'.format(name=name, val=val)
        command += self.command
        return command
