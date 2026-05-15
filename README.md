# FileFolderMeta
Calculate metadata from file(s) / folder(s) nested within a given path

## Installation
FileFolderMeta is written in Python and depends on the following packages:

* [Mutagen](https://pypi.org/project/mutagen)
* [NiemaFS](https://pypi.org/project/niemafs)
* [Pillow](https://pypi.org/project/pillow)

You can simply download [`FileFolderMeta.py`](https://github.com/niemasd/FileFolderMeta/releases/latest/download/FileFolderMeta.py) from the most recent Release to your machine and run it. If you require a [Wheel](https://packaging.python.org/en/latest/specifications/binary-distribution-format/), you can download [`wheelhouse.zip`](https://github.com/niemasd/FileFolderMeta/releases/latest/download/wheelhouse.zip), which contains `.whl` files for FileFolderMeta and all of its dependencies.

## Usage

You can run the [`FileFolderMeta.py`](FileFolderMeta.py) script to produce a JSON file containing metadata about file(s) and folder(s) nested within a given path. Run it with the `-h` flag to view the command-line arguments and usage.

Then, you can either open the JSON in your favorite JSON viewer / text editor, or you can use the companion [interactive web application](https://niema.net/FileFolderMeta) to view the metadata.

## Supported Formats
* Audio Files
* Binary Files
* Directories
* HFS (Apple) Disc/Volume Images
* Images
* ISO 9660 Disc Images (e.g. ISO, BIN)
* Nintendo GameCube Mini-DVD Images
* Nintendo GameCube RARC (.arc) Archives
* Nintendo GameCube TGC Images
* Nintendo Wii DVD Images
* ZIP Archives
