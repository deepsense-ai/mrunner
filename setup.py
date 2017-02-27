from setuptools import setup, find_packages
setup(
    name='mrunner',
    version='0.0.3',
    packages=find_packages(),
    install_requires=['PyYAML'],
    entry_points={
        'console_scripts': [
            'mrunner=mrunner.mrunner:main',
            'command_gen=mrunner.command_gen:main',
        ],
    },
)
