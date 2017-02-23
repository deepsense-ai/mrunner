from setuptools import setup, find_packages
setup(
    name='mrunner',
    version='0.0.3',
    py_modules=['mrunner'],
    install_requires=['PyYAML'],
    entry_points={
        'console_scripts': [
            'mrunner=mrunner:main',
        ],
    },
)
