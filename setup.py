from setuptools import setup, find_packages
setup(
    name='mrunner',
    version='0.0.15',
    packages=find_packages(),
    install_requires=['PyYAML', 'fabric'],
    entry_points={
        'console_scripts': [
            'mrunner_local=mrunner.mrunner_cli:main',
            'mrunner_plgrid=mrunner.mrunner_plgrid_cli:main',
            'mrunner_kube=mrunner.mrunner_kube_cli:main',
            'command_gen=mrunner.command_gen:main',
        ],
    },
)
