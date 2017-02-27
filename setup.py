from setuptools import setup, find_packages
setup(
    name='mrunner',
    version='0.0.3',
    packages=['mrunner'],
    #py_modules=['mrunner'],
    install_requires=['PyYAML'],
    entry_points={
        'console_scripts': [
            'mrunner=mrunner.mrunner:main',
            'command_gen=mrunner.command_gen:main',
        ],
    },
)
