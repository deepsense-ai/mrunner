# -*- coding: utf-8 -*-
import os
from subprocess import call

import attr
from docker.errors import ImageNotFound
from path import Path

from mrunner.utils.utils import GeneratedTemplateFile


class RequirementsFile(object):

    def __init__(self, path, requirements):
        self._path = Path(path)
        with open(path, 'w') as requirements_file:
            payload = '\n'.join(requirements)
            requirements_file.writelines(payload)

    def __del__(self):
        self._path.remove_p()

    @property
    def path(self):
        return self._path


StaticCmd = attr.make_class('StaticCmd', ['command', 'env'], frozen=True)


class DockerFile(GeneratedTemplateFile):
    DEFAULT_DOCKERFILE_TEMPLATE = 'Dockerfile.jinja2'

    def __init__(self, experiment, requirements_file):
        experiment_data = attr.asdict(experiment)
        # paths in command shall be relative
        cmd = experiment_data.pop('cmd')
        updated_cmd = self._rewrite_paths(experiment.cwd, cmd.command)
        experiment = attr.evolve(experiment, cmd=StaticCmd(command=updated_cmd, env=cmd.env))

        super(DockerFile, self).__init__(template_filename=self.DEFAULT_DOCKERFILE_TEMPLATE,
                                         experiment=experiment, requirements_file=requirements_file)

    def _rewrite_paths(self, cwd, cmd):
        updated_cmd = []
        for item in cmd.split(' '):
            if Path(item).exists():
                item = Path(cwd).relpathto(item)
            updated_cmd.append(item)
        return ' '.join(updated_cmd)


class DockerEngine(object):

    def __init__(self, docker_url=None):
        import docker
        base_url = docker_url if docker_url else os.environ.get('DOCKER_HOST', 'unix://var/run/docker.sock')
        self._client = docker.DockerClient(base_url=base_url)

    def _login_with_docker(self, experiment):
        self._client.login(registry=experiment.registry_url, username=experiment.registry_username,
                           password=experiment.registry_password, reauth=True)

    def _login_with_gcloud(self, experiment):
        call('gcloud auth configure-docker'.split(' '))

    def build_and_publish_image(self, experiment):

        registry_url = experiment.registry_url
        self._is_gcr = registry_url and registry_url.startswith('https://gcr.io')
        if registry_url:
            _login = self._login_with_gcloud if self._is_gcr else self._login_with_docker
            _login(experiment)

        # requirements filename shall be constant for experiment, to use docker cache during build;
        # thus we don't use dynamic/temporary file names
        requirements = RequirementsFile(self._generate_requirements_name(experiment), experiment.requirements)

        dockerfile = DockerFile(experiment=experiment, requirements_file=requirements.path)
        dockerfile_rel_path = Path(experiment.cwd).relpathto(dockerfile.path)

        # obtain old image for comparison if there where any changes
        repository_name = self._generate_repository_name(experiment)
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

    def _generate_requirements_name(self, experiment):
        return 'requirements_{}_{}.txt'.format(experiment.project, experiment.name)

    def _generate_repository_name(self, experiment):
        image_name = '{}/{}'.format(experiment.project, experiment.name)

        # while publishing images there is need to prefix them with repository hostname
        if experiment.registry_url:
            registry_name = experiment.registry_url.split(r'://')[1]
            image_name = '{}/{}'.format(registry_name, image_name)

            if self._is_gcr:
                assert experiment.google_project_id, 'Configure google_project_id key for current context'
                image_name = image_name.replace('/{}/'.format(experiment.project),
                                                '/{}/'.format(experiment.google_project_id))

        return image_name

    def _get_tag(self):
        from datetime import datetime
        return datetime.utcnow().strftime('%Y%m%d_%H%M%S')
