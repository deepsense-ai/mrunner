#!/usr/bin/env python
import sys

from mrunner import parser_to_yaml

config_path = sys.argv[1]

print parser_to_yaml(config_path)
