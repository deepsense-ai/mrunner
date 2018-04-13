# -*- coding: utf-8 -*-
import unittest

from path import Path

from mrunner.config import Context, Experiment
from mrunner.utils import GeneratedTemplateFile, DObject


class GeneratedTemplatesTestCase(unittest.TestCase):

    def test_generate_template(self):
        context = Context(storage='/storage')
        experiment = Experiment(base_image='python:3',
                                paths_to_copy=['.', 'src', 'tests'],
                                cmd=DObject(command='neptune run foo.py --storage /storage -- --epochs 2', env={}))
        print('xxx', experiment.cmd_without_params)
        dockerfile = GeneratedTemplateFile(template_filename='Dockerfile.jinja2',
                                           context=context, experiment=experiment, requirements_file='requirements.txt')
        dockerfile_payload = Path(dockerfile.path).text(encoding='utf-8')
        expected_dockerfile_payload = '''FROM python:3

ARG EXP_DIR=/experiment
ARG STORAGE_DIR=/storage

COPY requirements.txt ${EXP_DIR}/requirements.txt
RUN pip install --no-cache-dir -r $EXP_DIR/requirements.txt

COPY . ${EXP_DIR}/.
COPY src ${EXP_DIR}/src
COPY tests ${EXP_DIR}/tests

ENV STORAGE_DIR=${STORAGE_DIR}

VOLUME ${STORAGE_DIR}
VOLUME ${EXP_DIR}
WORKDIR ${EXP_DIR}

ENTRYPOINT ["neptune", "run", "foo.py", "--storage", "/storage", "--"]'''
        self.assertEqual(dockerfile_payload, expected_dockerfile_payload)
