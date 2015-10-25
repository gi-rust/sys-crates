#!/usr/bin/env python

import argparse
import subprocess
import logging
import os
import sys
from copy import copy

class Crate(object):
    def __init__(self, path, namespace, template=None):
        self.path = os.path.normcase(path)
        self.namespace = namespace
        self.template = template

# NOTE: The order of crates incorporates cross-crate dependencies.
# All crates that are dependencies of a crate in the list should precede
# that crate.
crates = [
    Crate(path='crates/glib-sys',
          namespace='GLib-2.0',
          template='glib-sys.tmpl'),
    Crate(path='crates/gobject-sys',
          namespace='GObject-2.0',
          template='gobject-sys.tmpl'),
]

python = sys.executable or 'python'

project_root = os.path.abspath(os.path.dirname(__file__))
tools_dir = os.path.join(project_root, 'tools')

tools_env = os.environ.copy()
if 'PYTHONPATH' in tools_env and tools_env['PYTHONPATH']:
    tools_env['PYTHONPATH'] = tools_dir + os.pathsep + tools_env['PYTHONPATH']
else:
    tools_env['PYTHONPATH'] = tools_dir

def _filter_crates(paths):
    if len(paths) == 0:
        return copy(crates)
    else:
        filter_set = set([os.path.normcase(os.path.normpath(path))
                          for path in paths])
        result = []
        for crate in crates:
            if crate.path in filter_set:
                result.append(crate)
                filter_set.remove(crate.path)
        if len(filter_set) != 0:
            if len(filter_set) == 1:
                msg = "unknown crate path: '{}'".format(filter_set.pop())
            else:
                msg = ("unknown crate paths: "
                       + ", ".join(["'{}'".format(p) for p in filter_set]))
            raise ValueError(msg)
        return result

def _run(args, **kwargs):
    # TODO: escape the arguments for logging with shlex.quote(),
    # when we live in the future and use Python 3.
    if 'cwd' in kwargs:
        logging.debug('Running (in %s) %s', kwargs['cwd'], ' '.join(args))
    else:
        logging.debug('Running %s', ' '.join(args))
        kwargs['cwd'] = project_root
    subprocess.check_call(args, **kwargs)

def install_tools(args):
    gen_srcdir = os.path.join(project_root, 'grust-gen')
    cmd_args = [python, 'setup.py']
    if not args.verbose:
        cmd_args.append('--quiet')
    cmd_args.extend(['develop', '--install-dir', tools_dir])
    _run(cmd_args, env=tools_env, cwd=gen_srcdir)

def generate(args):
    install_tools(args)

    grust_gen = os.path.join(tools_dir, 'grust-gen')
    for crate in _filter_crates(args.crate_paths):
        cmd_args = [grust_gen, '--sys', '--include-dir', 'gir']
        if crate.template:
            cmd_args.extend(['--template',
                             os.path.join(crate.path, crate.template)])
        cmd_args.extend(['--output', os.path.join(crate.path, 'lib.rs')])
        cmd_args.append(os.path.join('gir', crate.namespace + '.gir'))
        _run(cmd_args, env=tools_env)

def _add_crate_paths_argument(parser):
    parser.add_argument('crate_paths', metavar='PATH', nargs='*',
                        help='''Paths of crate submodules to process,
                                relative to the project root.
                                By default, all crates are processed.''')

def _get_arg_parser():
    parser = argparse.ArgumentParser(
            description='''
                Performs build tasks for the crates in this project.''')
    parser.add_argument('--verbose', action='store_true',
                        help='produce verbose output')
    subparsers = parser.add_subparsers(title='subcommands',
                                       help='one of the available commands')
    subp_generate = subparsers.add_parser(
            'generate',
            description='''
                Generate code for the crates in the project,
                using the GIR files from submodule 'gir'.''',
            help='generate code for the crates')
    subp_generate.set_defaults(command_func=generate)
    _add_crate_paths_argument(subp_generate)
    return parser

if __name__ == '__main__':
    arg_parser = _get_arg_parser()
    args = arg_parser.parse_args()
    logging.basicConfig(
            level=logging.DEBUG if args.verbose else logging.INFO,
            format='%(module)s:%(levelname)s: %(message)s')
    command_func = args.command_func
    command_func(args)
