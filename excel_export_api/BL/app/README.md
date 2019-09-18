# Excel Export API

## API configuration file
This JSON will file will be created upon completion of configuration of the Excel Export from the UI.

```python
{
  'header':{
    "field": {
      "header": "File",
      "width": 10
    }
  },
  'format': {
    'type': 'SPD/FPD/RPD',
    'name': 'Document ##' # only for SPD or FPD
  },
  'layout': {
    'type': 'horizontal/vertical/merged',
    'direction': 'top/bottom/left/right', # only for horizontal or vertical
    'gap': 2, # only for horizontal or vertical
    'repeat': True # only for merged
  },
  'output_path': 'path/to/the/directory',
  'name': 'Excel Output.xlsx'
}
```
### Headers
Each columns can be configured by the lead. The lead can configure the following parameters:
1. The order in which each column needs to be placed in the excel sheet.
2. `header (str)`: Text that needs to be displayed as the header for the corresponding field.
3. `field (str)`: The field name for the respective column
4. `width (int/str)`: The width of the column. It can be an integer value or `'auto'` which will automatically adjust the width based on the length of the values in the column.
5. `exclude (bool)`: Flag to exclude the column in excel or not.

### Format
#### SPD (Sheet Per Document)
1. `type (str)`: SPD. A new sheet will be added for every document that is processed. By default every sheet is named after the name of the document.
2. `name (str)`: *In future, the lead may specify how the sheets should be named).*

#### FPD (File Per Document)
1. `type (str)`: FPD. A new file will be created for every document that is processed. By default every excel file is named after the name of the document.
2. `name (str)`: *(In future, the lead may specify how the file should be named).*

#### RPD (Row Per Document)
1. `type (str)`: RPD. Every row in the excel file corresponds to a document that is processed.

### Layout
#### Horizontal
1. `type (str)`: Horizontal. The extracted table will be entered below the fields.
2. `direction (str)`: It will decide on which side the table data will be entered. It can be either `top` or `bottom`. *(default: bottom)*
3. `gap (int)`: The number of blank cells between the fields and the table data. *(default: 3)*

#### Vertical
1. `type (str)`: Vertical. The extracted table will be entered beside the fields.
2. `direction (str)`: It will decide on which side the table data will be entered. It can be either `left` or `right`. *(default: right)*
3. `gap (int)`: The number of blank cells between the fields and the table data. *(default: 3)*

#### Merged
1. `type (str)`: Merged. The table data will be consolidated with the fields data.
2.  `repeat (bool)`: It will decide if the field value should be repeated for every line item in the table data or not. *(default: True)*

## API Output

### On Success

```python
{
    "flag": True,
    "message": "Successfully exported to excel."
}
```
#### Success messages

1. `Successfully exported to excel.`: If the format type specified if anything apart from SPD, FPD or RPD.
2. `No data to export.`: If there is no processed data to export in the database.

### On Failure
```python
{
    "flag": False,
    "message": "Oops! Something went wrong."
}
```
#### Failure messages

1. `Unknown format 'XXX'`: If the format type specified if anything apart from SPD, FPD or RPD.
2. `Path is None.`: If the `output_path` given in the config file is null.
3. `File name is None.`: If the `name` given in the config file is null.
4. `File name is blank.`: If the `name` given in the config file is empty string.
5. `Path does not exist. 'path/to/wrong/directory'`: If the `output_path` given in the config file is an invalid directory.
6. `Error opening config file 'excel_config.json'.`: If any error occurs while opening `excel_config.json`. Possibly because the file is not created.
---

## Configurable Parameters

### Format
Format is how the processed document will be added to the excel  sheet. It can be one of these types:
1. [SPD](#SPD-Sheet-Per-Document) (Sheet Per Document)
2. [FPD](#FPD-File-Per-Document) (File Per Document)
3. [RPD](#RPD-Row-Per-Document) (Row Per Document)

### Layout
It is to decide how the extracted tables and fields from the document should be arranged. It can be one of these types:
1. [Horizontal](#Horizontal)
2. [Vertical](#Vertical)
3. [Merged](#Merged)

### Output Path
It is the directory in which the excel file(s) will be saved in.

### Name
The name of the excel file that is generated. (This parameter will be ignore if format is FPD).
