#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import random
import re

import sys

from mrunner.utils.utils import parse_argv

# NOTE(maciek): Code is copied from jobman: https://github.com/crmne/jobman
def generate_combination(repl):
    if repl == []:
        return []
    else:
        res = []
        x = repl[0]
        res1 = generate_combination(repl[1:])
        for y in x:
            if res1 == []:
                res.append([y])
            else:
                res.extend([[y] + r for r in res1])
        return res


def generate_commands(sp):
    # Find replacement lists in the arguments
    repl = []
    p = re.compile('\{\{\S*?\}\}')
    for arg in sp:
        reg = p.findall(arg)
        if len(reg) == 1:
            reg = p.search(arg)
            curargs = reg.group()[2:-2].split(",")
            newcurargs = []
            for curarg in curargs:
                new = p.sub(curarg, arg)
                newcurargs.append(new)
            repl.append(newcurargs)
        elif len(reg) > 1:
            s = p.split(arg)
            tmp = []
            for i in range(len(reg)):
                if s[i]:
                    tmp.append(s[i])
                tmp.append(reg[i][2:-2].split(","))
            i += 1
            if s[i]:
                tmp.append(s[i])
            repl.append(generate_combination(tmp, ''))
        else:
            repl.append([arg])

    argscombination = generate_combination(repl)
    args_modif = generate_combination([x for x in repl if len(x) > 1])

    return (argscombination, args_modif)


def my_generate_commands(argv, repeat=1):
    result = []
    res = generate_commands(argv[1:])
    for command, choice in zip(res[0], res[1]):
        command_str = ' '.join(command)
        result.append(command_str)
    result = repeat * result

    return result

def main():

    parser = argparse.ArgumentParser(description='Generate commands', fromfile_prefix_chars='@')
    parser.add_argument('--repeat', type=int, default=1, help='Repeat commands')
    parser.add_argument('--shuffle', action='store_true', help='Shuffle commands')
    parser.add_argument('--limit', type=int, help='Limit number of commands')

    args, proper_args = parse_argv(parser, sys.argv)

    commands = my_generate_commands(proper_args, repeat=args.repeat)
    if args.shuffle:
        random.shuffle(commands)
    if args.limit is not None:
        commands = commands[:args.limit]

    if len(commands) == 0:
        commands = [' '.join(argv)]

    print('\n'.join(commands))
    return 0


if __name__ == '__main__':
    sys.exit(main())
