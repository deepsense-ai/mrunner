from setuptools import setup, find_packages

setup(
    name='mrunner',
    version='0.1.88',
    packages=find_packages(),
    include_package_data=True,
    install_requires=['PyYAML', 'fabric3', 'path.py', 'jinja2', 'six', 'attrs>=17.3', 'click',
                      'docker', 'kubernetes>=5.0.0', 'google-cloud'],
    entry_points={
        'console_scripts': [
            'mrunner=mrunner.mrunner_cli:cli',
            'command_gen=mrunner.command_gen_cli:main',
        ],
    },
)
