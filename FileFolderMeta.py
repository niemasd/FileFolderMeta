#! /usr/bin/env python3
'''
Calculate metadata from file(s) / folder(s) nested within a given path
'''

# standard imports
from datetime import datetime
from gzip import open as gopen
from hashlib import md5, sha1, sha256
from json import dump as jdump
from pathlib import Path
from sys import stderr
from zlib import crc32
import argparse

# useful constants
VERSION = '0.0.1'
TIMESTAMP_FORMAT_STRING = "%Y-%m-%d %H:%M:%S %Z"

# hash functionto calculate
HASH_FUNCTIONS = {
    'crc32': lambda x: f'{crc32(x):08x}',
    'md5': lambda x: md5(x).hexdigest(),
    'sha1': lambda x: sha1(x).hexdigest(),
    'sha256': lambda x: sha256(x).hexdigest(),
}

# return the current time as a string
def get_time():
    return datetime.now().strftime(TIMESTAMP_FORMAT_STRING)

# print log message
def print_log(s='', end='\n', file=stderr):
    print('[%s] %s' % (get_time(), s), end=end, file=file)

# print error message and exit
def error(s, exitcode=1, file=stderr):
    print_log(s, file=file); exit(exitcode)

# class to represent the most generalized of entities (superclass of all other classes)
class Entity:
    def __init__(self, name):
        self.name = name
    def to_dict(self):
        return {
            'name': self.name,
        }

# class to represent files and directories on disk
class OnDisk(Entity):
    def __init__(self, path):
        super().__init__(path.name)
        self.path = path
    def to_dict(self):
        return super().to_dict()

# class to represent directories
class Directory(OnDisk):
    def __init__(self, path):
        super().__init__(path)
        self.contents = None # initialize upon first `__iter__` call
    def __iter__(self):
        if self.contents is None:
            self.contents = [get_obj(p) for p in self.path.glob('*')]
        return iter(self.contents)
    def to_dict(self):
        return super().to_dict() | {
            'format': 'DIR',
            'children': [child.to_dict() for child in self],
        }

# class to represent arbitrary files (last resort if type-specific class doesn't exist)
class File(OnDisk):
    def __init__(self, path):
        super().__init__(path)
        self.stat_result = None # initialize upon first `stat` call
        self.data = None # initialize upon first `get_data` call
    def stat(self):
        if self.stat_result is None:
            self.stat_result = self.path.stat()
        return self.stat_result
    def get_data(self):
        if self.data is None:
            with open(self.path, 'rb') as self_f:
                self.data = self_f.read()
        return self.data
    def get_timestamp(self):
        return datetime.fromtimestamp(self.stat().st_mtime).astimezone().strftime(TIMESTAMP_FORMAT_STRING)
    def to_dict(self):
        return super().to_dict() | {
            'format': 'FILE',
            'size': self.stat().st_size,
            'date': self.get_timestamp(),
        } | {k:HASH_FUNCTIONS[k](self.get_data()) for k in sorted(HASH_FUNCTIONS.keys())}

# map file formats to classes
INPUT_FORMAT_TO_CLASS = {
    'DIR': Directory,
    'FILE': File,
}

# try to return the appropriate directory/file object from a given path
def get_obj(path):
    # input path is a directory
    if path.is_dir():
        return Directory(path)

    # try to infer class from file extension as last resort
    else:
        ext = path.suffix.strip().lstrip('.').upper()
        if ext in INPUT_FORMAT_TO_CLASS:
            return INPUT_FORMAT_TO_CLASS[ext](path)
        else:
            return File(path)
INPUT_FORMAT_TO_CLASS['AUTO'] = get_obj

# parse user args
def parse_args():
    # use argparse to parse user arguments
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i', '--input', required=True, type=str, help="Input File/Folder")
    parser.add_argument('-o', '--output', required=False, type=str, default='stdout', help="Output JSON File")
    parser.add_argument('-oi', '--output_indent', required=False, type=int, default=None, help="Number of of Spaces per Indent in Output")
    args = parser.parse_args()

    # check args for validity before returning
    args.input = Path(args.input)
    if not args.input.exists():
        error("Input not found: %s" % args.input)
    if args.output != 'stdout':
        args.output = Path(args.output)
        if args.output.exists():
            error("Output exists: %s" % args.output)
    if (args.output_indent is not None) and (args.output_indent < 0):
        error("Number of spaces per indent must be non-negative: %s" % args.output_indent)
    return args

# main content
def main():
    # load input
    args = parse_args()
    print_log("Loading Input: %s" % args.input)
    root = get_obj(args.input)

    # write output
    print_log("Writing Output: %s" % args.output)
    if args.output == 'stdout':
        from sys import stdout as output_f
    elif args.output.suffix.strip().lower() == '.gz':
        output_f = gopen(args.output, 'wt')
    else:
        output_f = open(args.output, 'wt')
    jdump(root.to_dict(), output_f, indent=args.output_indent)
    output_f.write('\n')
    output_f.close()

# run tool
if __name__ == "__main__":
    main()
