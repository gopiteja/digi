# Table Merger Documentation
# merge_table
## merge_table_config

### button_id
ID of the button from `button_definition` to get the properties of the button.

### source_type
Type of the source data to merge. Possible values:
1. **api**: If the source data is coming from an API call. *(not developed)*
2. **db**: If the source data is a table from database.
3. **excel**: If the source data is from an excel sheet. *(not developed)*

### source_config
The configuration to retrieve data from the source. It changes depending on the `source_type`.
##### db
```jsonc=
{
    "database": "external", // Databse to fetch from
    "table": "source", // Table to fetch from
    "host": "127.0.0.1", // [OPTIONAL] SQL server host
    "port": 5000, // [OPTIONAL] SQL server port
    "user": "root", // [OPTIONAL] SQL server user
    "password": "root" // [OPTIONAL] SQL server password
}
```
> Note: If you want to use a custom SQL server you must provide `host`, `port`, `user` and `password` to connect to the server. If not provided, it will conenct to ACE server by default.

### source_columns
Columns to select from the source data. The value will be comma separated.

### join_on
Common column data from source and extracted table. The value will be comma separated.
For example: `description, desc` means join the 2 data using `description` column from extracted table and `desc` column from the external data source.

### how
The type of join. Possible values:
1. **inner**: Compares two tables and only returns results where a match exists. Records from the extracted table are duplicated when they match multiple results in the external data.
2. **left**: Keep all records from the extracted table no matter what and insert NULL values when the external data doesn't match.