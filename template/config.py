import argparse

def create_parser(parser=None):
    if parser is None:
        parser = argparse.ArgumentParser(description='')
    return parser

