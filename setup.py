from setuptools import setup, find_packages

setup(
    name='mrunner',
    version='0.0.16',
    packages=find_packages(),
    install_requires=['PyYAML', 'fabric3', 'neptune-cli'],
    entry_points={
        'console_scripts': [
            'mrunner_local=mrunner.local_cli:main',
            'mrunner_plgrid=mrunner.plgrid_cli:main',
            'mrunner_kube=mrunner.kubernetes_cli:main',
            'command_gen=mrunner.command_gen_cli:main',
        ],
    },
)
