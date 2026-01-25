# FileFolderMeta
Calculate metadata from file(s) / folder(s) nested within a given path

## Installation
FileFolderMeta is written in Python and depends on the [NiemaFS](https://github.com/niemasd/NiemaFS) Python package. You can simply download [`FileFolderMeta.py`](FileFolderMeta.py) to your machine and run it.

## Usage

You can run the [`FileFolderMeta.py`](FileFolderMeta.py) script to produce a JSON file containing metadata about file(s) and folder(s) nested within a given path. Run it with the `-h` flag to view the command-line arguments and usage.

Then, you can either open the JSON in your favorite JSON viewer / text editor, or you can use the companion [interactive web application](https://niema.net/FileFolderMeta) to view the metadata.

## Supported Formats
* Binary Files
* Directories
* ISO 9660 Disc Images (e.g. ISO, BIN)
* Nintendo GameCube Mini-DVD Images
* Nintendo GameCube RARC (.arc) Archives
* Nintendo GameCube TGC Images
* Nintendo Wii DVD Images
* ZIP Archives
