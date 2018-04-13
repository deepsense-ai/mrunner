# -*- coding: utf-8 -*-
import os
from subprocess import call

from docker.errors import ImageNotFound
from path import Path

from mrunner.utils import GeneratedTemplateFile, DObject


class RequirementsFile(object):

    def __init__(self, path, requirements):
        self._path = Path(path)
        with open(path, 'w') as requirements_file:
            payload = '\n'.join(requirements).encode(encoding='utf-8')
            requirements_file.writelines(payload)

    def __del__(self):
        self._path.remove_p()

    @property
    def path(self):
        return self._path


class DockerFile(GeneratedTemplateFile):
    DEFAULT_DOCKERFILE_TEMPLATE = 'Dockerfile.jinja2'

    def __init__(self, context, experiment, requirements_file):
        from mrunner.experiment import Experiment
        experiment_data = experiment.to_dict()
        # paths in command shall be relative
        cmd = experiment_data.pop('cmd')
        updated_cmd = self._rewrite_paths(experiment.cwd, cmd.command)
        experiment = Experiment(cmd=DObject(command=updated_cmd, env=cmd.env), **experiment_data)
        super(DockerFile, self).__init__(template_filename=self.DEFAULT_DOCKERFILE_TEMPLATE,
                                         context=context, experiment=experiment, requirements_file=requirements_file)

    def _rewrite_paths(self, cwd, cmd):
        updated_cmd = []
        for item in cmd.split(' '):
            if Path(item).exists():
                item = Path(cwd).relpathto(item)
            updated_cmd.append(item)
        return ' '.join(updated_cmd)


class DockerEngine(object):

    def __init__(self, context, docker_url=None):
        import docker
        base_url = docker_url if docker_url else os.environ.get('DOCKER_HOST', 'unix://var/run/docker.sock')
        self._context = context
        self._client = docker.DockerClient(base_url=base_url)
        self._is_gcr = context.registry_url and context.registry_url.startswith('https://gcr.io')
        if context.registry_url:
            _login = self._login_with_gcloud if self._is_gcr else self._login_with_docker
            _login(context)

    def _login_with_docker(self, context):
        self._client.login(registry=context.registry_url, username=context.registry_username,
                           password=context.registry_password, reauth=True)

    def _login_with_gcloud(self, context):
        call('gcloud auth configure-docker'.split(' '))

    def build_and_publish_image(self, experiment):
        # requirements filename shall be constant for experiment, to use docker cache during build;
        # thus we don't use dynamic/temporary file names
        requirements = RequirementsFile(self._generate_requirements_name(self._context, experiment),
                                        experiment.requirements)

        dockerfile = DockerFile(context=self._context, experiment=experiment, requirements_file=requirements.path)
        dockerfile_rel_path = Path(experiment.cwd).relpathto(dockerfile.path)

        # obtain old image for comparison if there where any changes
        repository_name = self._generate_repository_name(self._context, experiment)
        try:
            old_image = self._client.images.get(repository_name + ':latest')
        except ImageNotFound:
            old_image = None

        # build image; use cache if possible
        image, _ = self._client.images.build(path=experiment.cwd, tag=repository_name,
                                             dockerfile=dockerfile_rel_path, pull=True, rm=True, forcerm=True)

        is_image_updated = not old_image or old_image.id != image.id
        if is_image_updated:
            # if new image is generated - tag it and push to repository
            tag = self._get_tag()
            image.tag(repository_name, tag=tag)
            result = self._client.images.push(repository_name, tag=tag)
            if 'errorDetail' in result:
                raise RuntimeError(result)
            image = self._client.images.get(repository_name)

        # obtain image name with our tag
        return [tag for tag in image.tags if not tag.endswith('latest')][0]

    def _generate_requirements_name(self, context, experiment):
        return 'requirements_{}_{}.txt'.format(experiment.project_name, experiment.name)

    def _generate_repository_name(self, context, experiment):
        image_name = '{}/{}'.format(experiment.project_name, experiment.name)

        # while publishing images there is need to prefix them with repository hostname
        if context.registry_url:
            registry_name = context.registry_url.split(r'://')[1]
            image_name = '{}/{}'.format(registry_name, image_name)

            if self._is_gcr:
                assert context.google_project_id, 'Configure google_project_id key for current context'
                image_name = image_name.replace('/{}/'.format(experiment.project_name),
                                                '/{}/'.format(context.google_project_id))

        return image_name

    def _get_tag(self):
        from datetime import datetime
        return datetime.utcnow().strftime('%Y%m%d_%H%M%S')
