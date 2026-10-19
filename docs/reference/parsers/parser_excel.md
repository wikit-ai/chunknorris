# Reference for `ExcelParser`

The ``ExcelParser`` enables parsing spreadsheets, such as .xslx files. All sheets in the notebook will be parsed.

::: chunknorris.parsers.sheets.excel_parser.ExcelParser
    handler: python
    options:
      show_source: false

## Inspecting a file before parsing

``ExcelParser.inspect_file()`` (or ``inspect_string()`` for bytes) describes each sheet without loading it entirely: the metrics are computed on the first ``n_sample_rows`` rows, and the row count is read from the file metadata. It can be used to route very long CSV-like files before parsing them.

```py
from chunknorris.parsers import ExcelParser

profiles = ExcelParser().inspect_file("myfile.xlsx")
for sheet_name, profile in profiles.items():
    print(sheet_name, profile.n_rows, profile.is_csv_like)
```

::: chunknorris.parsers.sheets.sheet_profile.SheetProfile
    handler: python
    options:
      show_source: false
