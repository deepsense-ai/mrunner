from setuptools import setup, find_packages
setup(
    name='mrunner',
    version='0.0.14',
    packages=find_packages(),
    install_requires=['PyYAML'],
    entry_points={
        'console_scripts': [
            'mrunner=mrunner.mrunner_cli:main',
            'mrunner_plgrid=mrunner.mrunner_plgrid_cli:main',
            'command_gen=mrunner.command_gen:main',
        ],
    },
)
