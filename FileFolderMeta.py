#! /usr/bin/env python3
'''
Calculate metadata from file(s) / folder(s) nested within a given path
'''

# standard imports
from datetime import datetime
from gzip import open as gopen
from hashlib import md5, sha1, sha256
from io import BytesIO
from json import dump as jdump
from pathlib import Path
from sys import stderr
from zlib import crc32
import argparse

# useful constants
VERSION = '0.0.4'
TIMESTAMP_FORMAT_STRING = "%Y-%m-%d %H:%M:%S"

# hash functionto calculate
HASH_FUNCTIONS = {
    'crc32': lambda x: '0x' + f'{crc32(x):08x}',
    'md5': lambda x: '0x' + md5(x).hexdigest(),
    'sha1': lambda x: '0x' + sha1(x).hexdigest(),
    'sha256': lambda x: '0x' + sha256(x).hexdigest(),
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

# non-standard imports
try:
    from niemafs import IsoFS, ZipFS
except:
    error("Unable to import 'niemafs'. Install with: pip install niemafs")

# class to represent the most generalized of entities (superclass of all other classes)
class FFM_Entity:
    def __init__(self, name):
        self.name = name
    def to_dict(self):
        return {
            'name': self.name,
        }

# class to represent files and directories on disk
class FFM_OnDisk(FFM_Entity):
    def __init__(self, path):
        super().__init__(path.name)
        self.path = path
    def to_dict(self):
        return super().to_dict()

# class to represent directories
class FFM_Directory(FFM_OnDisk):
    def __init__(self, path):
        super().__init__(path)
        self.children = None # initialize upon first `__iter__` call
    def __iter__(self):
        if self.children is None:
            self.children = sorted((get_obj(p) for p in self.path.glob('*')), key=lambda x: x.name)
        return iter(self.children)
    def to_dict(self):
        return super().to_dict() | {
            'format': 'DIR',
            'children': [child.to_dict() for child in self],
        }

# class to represent arbitrary files (last resort if type-specific class doesn't exist)
class FFM_File(FFM_OnDisk):
    def __init__(self, path):
        super().__init__(path)
        self.data = None # initialize upon first `get_data` call
        self.stat_result = None # initialize upon first `stat` call
        self.timestamp = None # initialize upon first `get_timestamp` call
    def get_data(self):
        if self.data is None:
            with open(self.path, 'rb') as self_f:
                self.data = self_f.read()
        return self.data
    def get_size(self):
        return len(self.get_data())
    def stat(self):
        if self.stat_result is None:
            self.stat_result = self.path.stat()
        return self.stat_result
    def get_timestamp(self):
        if self.timestamp is None:
            self.timestamp = datetime.fromtimestamp(self.stat().st_mtime).astimezone().strftime(TIMESTAMP_FORMAT_STRING)
        return self.timestamp
    def to_dict(self):
        return super().to_dict() | {
            'format': 'FILE',
            'size': self.get_size(),
            'date': self.get_timestamp(),
        } | {k:HASH_FUNCTIONS[k](self.get_data()) for k in sorted(HASH_FUNCTIONS.keys())}

# class to represent ZIP files
class FFM_ZipArchive(FFM_File):
    def __init__(self, path):
        super().__init__(path)
        self.children = None # initialize upon first `__iter__` call
        self.zip = None
    def __iter__(self):
        if self.children is None:
            if self.zip is None:
                self.zip = ZipFS(BytesIO(self.get_data()), 'r')
            self.children = list()
            zip_path_to_obj = dict()
            for zip_path, zip_timestamp, zip_data in self.zip:
                if zip_data is None:
                    obj = FFM_Directory(zip_path)
                else:
                    obj = get_obj(zip_path)
                    obj.data = zip_data
                    obj.timestamp = zip_timestamp.strftime(TIMESTAMP_FORMAT_STRING)
                if '/' in str(zip_path):
                    parent_obj = zip_path_to_obj[zip_path.parent]
                    if parent_obj.children is None:
                        parent_obj.children = list()
                    parent_obj.children.append(obj)
                else:
                    self.children.append(obj)
                zip_path_to_obj[zip_path] = obj
        return iter(self.children)
    def to_dict(self):
        out = super().to_dict() | {
            'children': [child.to_dict() for child in self],
        }
        out['format'] = 'ZIP'
        return out

# class to represent ISO files
class FFM_IsoArchive(FFM_File):
    def __init__(self, path):
        super().__init__(path)
        self.children = None # initialize upon first `__iter__` call
        self.iso = None
    def __iter__(self):
        if self.children is None:
            if self.iso is None:
                self.iso = IsoFS(BytesIO(self.get_data()), 'r')
            self.children = list()
            iso_path_to_obj = dict()
            for iso_path, iso_timestamp, iso_data in self.iso:
                if iso_data is None:
                    obj = FFM_Directory(iso_path)
                else:
                    obj = get_obj(iso_path)
                    obj.data = iso_data
                    obj.timestamp = iso_timestamp.strftime(TIMESTAMP_FORMAT_STRING)
                if '/' in str(iso_path):
                    parent_obj = iso_path_to_obj[iso_path.parent]
                    if parent_obj.children is None:
                        parent_obj.children = list()
                    parent_obj.children.append(obj)
                else:
                    self.children.append(obj)
                iso_path_to_obj[iso_path] = obj
        return iter(self.children)
    def to_dict(self):
        out = super().to_dict() | {
            'children': [child.to_dict() for child in self],
        }
        # add IsoFS attributes
        out['physical_logical_block_size'] = self.iso.get_physical_logical_block_size()
        out['user_data_offset'] = self.iso.get_user_data_offset()
        out['user_data_size'] = self.iso.get_user_data_size()
        out['logical_block_size'] = self.iso.get_logical_block_size()
        for k, v in self.iso.parse_primary_volume_descriptor().items():
            if k.endswith('_identifier'):
                out[k] = v
            elif k.endswith('_datetime'):
                try:
                    out[k] = v.strftime(TIMESTAMP_FORMAT_STRING)
                except:
                    out[k] = str(v)
        out['format'] = 'ISO'
        return out

# map file formats to classes
INPUT_FORMAT_TO_CLASS = {
    'BIN':  FFM_IsoArchive,
    'DIR':  FFM_Directory,
    'FILE': FFM_File,
    'ISO':  FFM_IsoArchive,
    'ZIP':  FFM_ZipArchive,
}

# try to return the appropriate directory/file object from a given path
def get_obj(path):
    # input path is a directory
    if path.is_dir():
        return FFM_Directory(path)

    # try to infer class from file extension as last resort
    ext = path.suffix.strip().lstrip('.').upper()
    if ext in INPUT_FORMAT_TO_CLASS:
        try:
            tmp = INPUT_FORMAT_TO_CLASS[ext](path)
            list(tmp) # trigger actually setting up object
            return tmp
        except:
            pass # if fails (e.g. BIN is just a binary file, not ISO), just default to FFM_File
    return FFM_File(path)
INPUT_FORMAT_TO_CLASS['AUTO'] = get_obj

# parse user args
def parse_args():
    # use argparse to parse user arguments
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i', '--input', required=True, type=str, help="Input File/Folder")
    parser.add_argument('-o', '--output', required=False, type=str, default='stdout', help="Output JSON File")
    parser.add_argument('-oi', '--output_indent', required=False, type=int, default=None, help="Number of of Spaces per Indent in Output JSON")
    parser.add_argument('-os', '--output_sort', action='store_true', help="Sort Keys in Output JSON Alphabetically")
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
    jdump(root.to_dict(), output_f, indent=args.output_indent, sort_keys=args.output_sort)
    output_f.write('\n')
    output_f.close()

# run tool
if __name__ == "__main__":
    main()
