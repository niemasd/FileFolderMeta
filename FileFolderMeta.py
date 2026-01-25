#! /usr/bin/env python3
'''
Calculate metadata from file(s) / folder(s) nested within a given path
'''

# standard imports
from datetime import datetime
from hashlib import md5, sha1, sha256
from io import BytesIO
from json import dump as jdump
from pathlib import Path
from sys import stderr
from warnings import warn
from zlib import crc32
import argparse
import gzip
import lzma

# useful constants
__version__ = '0.0.15'
TIMESTAMP_FORMAT_STRING = "%Y-%m-%d %H:%M:%S"
COMPRESSED_EXTENSIONS = {'GZ', 'XZ'}

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
    from niemafs import GcmFS, IsoFS, TarFS, TgcFS, ZipFS
except:
    error("Unable to import 'niemafs'. Install with: pip install niemafs")
FORMAT_TO_NIEMAFS = {
    'GCM': GcmFS,
    'ISO': IsoFS,
    'TAR': TarFS,
    'TGC': TgcFS,
    'ZIP': ZipFS,
}
try:
    from niemafs import WiiFS
    FORMAT_TO_NIEMAFS['WII'] = WiiFS
except:
    warn("Unable to import 'niemafs.WiiFS' (likely due to missing dependencies). Wii support disabled.")
    WiiFS = None

# clean a file extension
def clean_ext(ext):
    return ext.replace('.','').strip().upper()

# decompress a data stream, or return it if already decompressed
def decompress(path, data):
    ext = clean_ext(path.suffix)
    if ext == 'GZ':
        return gzip.decompress(data)
    elif ext == 'XZ':
        return lzma.decompress(data)
    else:
        return data

# class to represent the most generalized of entities (superclass of all other classes)
class FFM_Entity:
    def __init__(self, name, data=None):
        self.name = name
        self.data = data # initialize upon first `get_data` call if `None`
    def to_dict(self):
        return {'name': self.name}

# class to represent files and directories on disk
class FFM_OnDisk(FFM_Entity):
    def __init__(self, path, data=None):
        super().__init__(name=path.name, data=data)
        self.path = path
    def to_dict(self):
        return super().to_dict()

# class to represent directories
class FFM_Directory(FFM_OnDisk):
    def __init__(self, path):
        super().__init__(path=path, data=None)
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
    def __init__(self, path, data=None):
        super().__init__(path=path, data=data)
        self.stat_result = None # initialize upon first `stat` call
        self.create_time = None # initialize upon first call to `get_create_time` call
        self.mod_time = None # initialize upon first `get_mod_time` call
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
    def get_create_time(self):
        if self.create_time == '': # '' denotes an intentionally blank time (e.g. file systems that don't have timestamps)
            return None
        if self.create_time is None:
            self.create_time = datetime.fromtimestamp(self.stat().st_ctime).astimezone().strftime(TIMESTAMP_FORMAT_STRING)
        return self.create_time
    def get_mod_time(self):
        if self.mod_time == '': # '' denotes an intentionally blank time (e.g. file systems that don't have timestamps)
            return None
        if self.mod_time is None:
            self.mod_time = datetime.fromtimestamp(self.stat().st_mtime).astimezone().strftime(TIMESTAMP_FORMAT_STRING)
        return self.mod_time
    def to_dict(self):
        out = super().to_dict() | {
            'format': 'FILE',
            'size': self.get_size(),
        } | {k:HASH_FUNCTIONS[k](self.get_data()) for k in sorted(HASH_FUNCTIONS.keys())}
        for k, func in [('create_time',self.get_create_time), ('mod_time',self.get_mod_time)]:
            v = func()
            if v is not None:
                out[k] = v
        return out

# class to represent NiemaFS-based classes
class FFM_NiemaFS(FFM_File):
    def __init__(self, fmt, path, data=None):
        super().__init__(path=path, data=data)
        self.children = None # initialize upon first `__iter__` call
        self.format = fmt
        self.fs = None

    def __iter__(self):
        if self.children is None:
            if self.fs is None:
                self.fs = FORMAT_TO_NIEMAFS[self.format](BytesIO(decompress(self.path, self.get_data())))
            self.children = list()
            fs_path_to_obj = dict()
            for curr_path, curr_mod_time, curr_data in self.fs:
                if curr_data is None:
                    obj = FFM_Directory(curr_path)
                else:
                    obj = get_obj(path=curr_path, data=curr_data)
                    obj.data = curr_data
                    obj.create_time = ''
                    if curr_mod_time is None:
                        obj.mod_time = ''
                    else:
                        obj.mod_time = curr_mod_time.strftime(TIMESTAMP_FORMAT_STRING)
                if '/' in str(curr_path):
                    parent_obj = fs_path_to_obj[curr_path.parent]
                    if parent_obj.children is None:
                        parent_obj.children = list()
                    parent_obj.children.append(obj)
                else:
                    self.children.append(obj)
                fs_path_to_obj[curr_path] = obj
        return iter(self.children)

    def to_dict(self):
        # universal NiemaFS attributes
        out = super().to_dict() | {
            'children': [child.to_dict() for child in self],
        }

        # ISO-specific attributes
        if self.format == 'ISO':
            out['physical_logical_block_size'] = self.fs.get_physical_logical_block_size()
            out['user_data_offset'] = self.fs.get_user_data_offset()
            out['user_data_size'] = self.fs.get_user_data_size()
            out['logical_block_size'] = self.fs.get_logical_block_size()
            for k, v in self.fs.parse_primary_volume_descriptor().items():
                if k.endswith('_identifier'):
                    out[k] = v
                elif k.endswith('_datetime'):
                    try:
                        out[k] = v.strftime(TIMESTAMP_FORMAT_STRING)
                    except:
                        out[k] = str(v)

        # GameCube-specific attributes
        elif self.format == 'GCM':
            gcm_boot_bin = self.fs.parse_boot_bin()
            for k in ['game_code', 'maker_code', 'disk_id', 'version', 'game_name']:
                out[k] = gcm_boot_bin[k]

        # Wii-specific attributes
        elif self.format == 'WII':
            wii_header = self.fs.parse_header()
            for k in ['game_code', 'maker_code', 'disk_id', 'version', 'game_name']:
                out[k] = wii_header[k]

        # finish up
        out['format'] = self.format
        return out

# class to represent ZIP files
class FFM_ZipArchive(FFM_NiemaFS):
    def __init__(self, path, data=None):
        super().__init__(fmt='ZIP', path=path, data=data)

# class to represent TAR files
class FFM_TarArchive(FFM_NiemaFS):
    def __init__(self, path, data=None):
        super().__init__(fmt='TAR', path=path, data=data)

# class to represent ISO files
class FFM_IsoArchive(FFM_NiemaFS):
    def __init__(self, path, data=None):
        super().__init__(fmt='ISO', path=path, data=data)

# class to represent GameCube mini-DVDs
class FFM_GcmArchive(FFM_NiemaFS):
    def __init__(self, path, data=None):
        super().__init__(fmt='GCM', path=path, data=data)

# class to represent GameCube TGC files
class FFM_TgcArchive(FFM_GcmArchive):
    def __init__(self, path, data=None):
        super().__init__(path=path, data=data)
        self.format = 'TGC'

# class to represent Wii DVDs
class FFM_WiiArchive(FFM_NiemaFS):
    def __init__(self, path, data=None):
        super().__init__(fmt='WII', path=path, data=data)

# map file formats to classes
INPUT_FORMAT_TO_CLASS = {
    'BIN':  FFM_IsoArchive,
    'DIR':  FFM_Directory,
    'FILE': FFM_File,
    'GCM':  FFM_GcmArchive,
    'ISO':  FFM_IsoArchive,
    'TAR':  FFM_TarArchive,
    'TGC':  FFM_TgcArchive,
    'ZIP':  FFM_ZipArchive,
}
if WiiFS is not None:
    INPUT_FORMAT_TO_CLASS['WII'] = FFM_WiiArchive

# try to return the appropriate directory/file object from a given path
def get_obj(path, data=None):
    # input path is a directory
    if path.is_dir():
        return FFM_Directory(path)

    # try to infer class from file extension as last resort
    ext = clean_ext(path.suffix)
    if ext in COMPRESSED_EXTENSIONS:
        ext = clean_ext(path.suffixes[-2])
    if ext in INPUT_FORMAT_TO_CLASS:
        try:
            tmp = INPUT_FORMAT_TO_CLASS[ext](path, data=data)
            list(tmp) # trigger actually setting up object
            return tmp
        except:
            pass # if fails (e.g. BIN is just a binary file, not ISO), just default to FFM_File
    return FFM_File(path, data=data)
INPUT_FORMAT_TO_CLASS['AUTO'] = get_obj

# parse user args
def parse_args():
    # use argparse to parse user arguments
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i', '--input', required=True, type=str, help="Input File/Folder")
    parser.add_argument('-if', '--input_format', required=False, type=str, default='AUTO', help="Input File Format (options: %s)" % ', '.join(sorted(INPUT_FORMAT_TO_CLASS.keys())))
    parser.add_argument('-o', '--output', required=False, type=str, default='stdout', help="Output JSON File")
    parser.add_argument('-oi', '--output_indent', required=False, type=int, default=None, help="Number of Spaces per Indent in Output JSON")
    parser.add_argument('-oit', '--output_indent_tab', action='store_true', help="Use Tabs (instead of spaces) for Indents in Output JSON")
    parser.add_argument('-os', '--output_sort', action='store_true', help="Sort Keys in Output JSON Alphabetically")
    args = parser.parse_args()

    # check args for validity before returning
    args.input = Path(args.input)
    if not args.input.exists():
        error("Input not found: %s" % args.input)
    args.input_format = args.input_format.strip().upper()
    if args.input_format not in INPUT_FORMAT_TO_CLASS:
        raise ValueError("Invalid input format (%s). Options: %s" % (args.input_format, ', '.join(sorted(INPUT_FORMAT_TO_CLASS.keys()))))
    if args.output != 'stdout':
        args.output = Path(args.output)
        if args.output.exists():
            error("Output exists: %s" % args.output)
    if (args.output_indent is not None) and (args.output_indent < 0):
        error("Number of spaces per indent must be non-negative: %s" % args.output_indent)
    if args.output_indent_tab:
        if args.output_indent is None:
            args.output_indent = '\t'
        else:
            args.output_indent = args.output_indent * '\t'
    return args

# main content
def main():
    # load input
    args = parse_args()
    print_log("Loading Input: %s" % args.input)
    if args.input_format == 'AUTO':
        print_log("Attempting to automatically infer input format...")
        root = get_obj(args.input)
    else:
        print_log("Using user-provided input format: %s" % args.input_format)
        root = INPUT_FORMAT_TO_CLASS[args.input_format](args.input)

    # write output
    print_log("Writing Output: %s" % args.output)
    if args.output == 'stdout':
        from sys import stdout as output_f
    elif args.output.suffix.strip().lower() == '.gz':
        output_f = gzip.open(args.output, 'wt')
    else:
        output_f = open(args.output, 'wt')
    jdump(root.to_dict(), output_f, indent=args.output_indent, sort_keys=args.output_sort)
    output_f.write('\n')
    output_f.close()

# run tool
if __name__ == "__main__":
    main()
