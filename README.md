# FileFolderMeta
Calculate metadata from file(s) / folder(s) nested within a given path

## Usage

You can run the [`FileFolderMeta.py`](FileFolderMeta.py) script to produce a JSON file containing metadata about file(s) and folder(s) nested within a given path:

```
FileFolderMeta.py [-h] -i INPUT [-o OUTPUT] [-oi OUTPUT_INDENT] [-os]

Calculate metadata from file(s) / folder(s) nested within a given path

options:
  -h, --help                                         show this help message and exit
  -i INPUT, --input INPUT                            Input FFM_File/Folder (default: None)
  -o OUTPUT, --output OUTPUT                         Output JSON FFM_File (default: stdout)
  -oi OUTPUT_INDENT, --output_indent OUTPUT_INDENT   Number of of Spaces per Indent in Output JSON (default: None)
  -os, --output_sort                                 Sort Keys in Output JSON Alphabetically (default: False)
```

Then, you can either open the JSON in your favorite JSON viewer / text editor, or you can use the companion [interactive web application](https://niema.net/FileFolderMeta) to view the metadata.
