# Google Sheets API

Google Sheets tools for spreadsheet creation, data management, formatting, and charting.

**12 tools available**

## Overview

The Google Sheets integration provides comprehensive spreadsheet functionality including:

- **Data Management**: Create, read, update spreadsheets and sheets
- **Cell Operations**: Get/set values, clear ranges, append data
- **Formatting**: Cell formatting, number formats, merge cells, column widths
- **Charts**: Create bar, line, and pie charts from data
- **Advanced Features**: Conditional formatting (coming soon)

## Authentication Required

All Sheets tools require authentication with the following scope:
- `https://www.googleapis.com/auth/spreadsheets`

## Tools

### create_spreadsheet

Create a new Google Spreadsheet.

**Parameters:**
- `title` (string, required): Title for the new spreadsheet

**Returns:**
- `spreadsheet_id`: Unique identifier for the created spreadsheet
- `title`: Spreadsheet title
- `url`: Direct link to open the spreadsheet
- `status`: Creation status

**Example:**
```json
{
  "title": "Q4 2024 Sales Report"
}
```

---

### get_spreadsheet_data

Get spreadsheet metadata and structure including all sheets.

**Parameters:**
- `spreadsheet_id` (string, required): The spreadsheet ID

**Returns:**
- `spreadsheet_id`: The spreadsheet identifier
- `title`: Spreadsheet title
- `sheets`: Array of sheet metadata (name, id, properties)
- `url`: Direct link to the spreadsheet

**Example:**
```json
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
}
```

---

### list_spreadsheet_sheets

List all sheets/tabs in a spreadsheet.

**Parameters:**
- `spreadsheet_id` (string, required): The spreadsheet ID

**Returns:**
- `spreadsheet_id`: The spreadsheet identifier
- `sheets`: Array of sheet information (name, index, id, properties)

**Example:**
```json
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
}
```

---

### get_sheet_values

Get values from a specific sheet/tab as CSV format.

**Parameters:**
- `spreadsheet_id` (string, required): The spreadsheet ID
- `sheet_name` (string, required): Name of the sheet/tab
- `range` (string, optional): A1 notation range (default: "A:ZZ")

**Returns:**
- `spreadsheet_id`: The spreadsheet identifier
- `sheet_name`: Name of the sheet
- `range`: A1 notation range that was read
- `data`: CSV formatted data
- `row_count`: Number of rows returned
- `column_count`: Number of columns in the data

**Example:**
```json
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "sheet_name": "Sales Data",
  "range": "A1:D10"
}
```

---

### update_sheet_values

Update specific cells in a sheet with new values.

**Parameters:**
- `spreadsheet_id` (string, required): The spreadsheet ID
- `sheet_name` (string, required): Name of the sheet/tab
- `range` (string, required): A1 notation range to update
- `values` (array, required): 2D array of values to write

**Returns:**
- `spreadsheet_id`: The spreadsheet identifier
- `updated_range`: A1 notation of the updated range
- `updated_rows`: Number of rows updated
- `updated_columns`: Number of columns updated
- `updated_cells`: Total number of cells updated

**Example:**
```json
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "sheet_name": "Sales Data",
  "range": "A1:B2",
  "values": [
    ["Product", "Sales"],
    ["Widget A", "150"]
  ]
}
```

---

### append_sheet_values

Append rows to the end of existing data in a sheet.

**Parameters:**
- `spreadsheet_id` (string, required): The spreadsheet ID
- `sheet_name` (string, required): Name of the sheet/tab
- `values` (array, required): 2D array of values to append

**Returns:**
- `spreadsheet_id`: The spreadsheet identifier
- `updated_range`: A1 notation of where data was appended
- `updated_rows`: Number of rows added
- `updated_columns`: Number of columns updated
- `updated_cells`: Total number of cells updated

**Example:**
```json
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "sheet_name": "Sales Data",
  "values": [
    ["Widget B", "200"],
    ["Widget C", "175"]
  ]
}
```

---

### clear_sheet_values

Clear values from a specific range in a sheet.

**Parameters:**
- `spreadsheet_id` (string, required): The spreadsheet ID
- `sheet_name` (string, required): Name of the sheet/tab
- `range` (string, required): A1 notation range to clear

**Returns:**
- `spreadsheet_id`: The spreadsheet identifier
- `cleared_range`: A1 notation of the cleared range
- `status`: Confirmation of clearing operation

**Example:**
```json
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "sheet_name": "Sales Data",
  "range": "A10:D15"
}
```

---

### format_cells

Apply visual formatting to cells including colors, fonts, borders, and text styles.

**Parameters:**
- `spreadsheet_id` (string, required): The spreadsheet ID
- `sheet_name` (string, required): Name of the sheet/tab
- `range` (string, required): A1 notation range to format
- `background_color` (object, optional): RGB color object `{"red": 1.0, "green": 0.0, "blue": 0.0}`
- `text_color` (object, optional): RGB color object for text
- `bold` (boolean, optional): Apply bold formatting
- `italic` (boolean, optional): Apply italic formatting
- `font_size` (integer, optional): Font size (8-400)
- `font_family` (string, optional): Font family name
- `borders` (object, optional): Border configuration

**Returns:**
- `spreadsheet_id`: The spreadsheet identifier
- `formatted_range`: A1 notation of the formatted range
- `status`: Confirmation of formatting operation

**Example:**
```json
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "sheet_name": "Sales Data",
  "range": "A1:D1",
  "background_color": {"red": 0.2, "green": 0.6, "blue": 1.0},
  "text_color": {"red": 1.0, "green": 1.0, "blue": 1.0},
  "bold": true,
  "font_size": 12
}
```

---

### set_number_format

Set number formatting for cells (currency, percentage, date formats, etc.).

**Parameters:**
- `spreadsheet_id` (string, required): The spreadsheet ID
- `sheet_name` (string, required): Name of the sheet/tab
- `range` (string, required): A1 notation range to format
- `number_format` (string, required): Format pattern (e.g., "$#,##0.00", "0.00%", "mm/dd/yyyy")

**Returns:**
- `spreadsheet_id`: The spreadsheet identifier
- `formatted_range`: A1 notation of the formatted range
- `number_format`: Applied number format
- `status`: Confirmation of formatting operation

**Common Format Examples:**
- Currency: `"$#,##0.00"`
- Percentage: `"0.00%"`
- Date: `"mm/dd/yyyy"`
- Scientific: `"0.00E+00"`

**Example:**
```json
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "sheet_name": "Sales Data",
  "range": "B2:B10",
  "number_format": "$#,##0.00"
}
```

---

### merge_cells

Merge cells across a specified range.

**Parameters:**
- `spreadsheet_id` (string, required): The spreadsheet ID
- `sheet_name` (string, required): Name of the sheet/tab
- `range` (string, required): A1 notation range to merge
- `merge_type` (string, optional): Type of merge ("MERGE_ALL", "MERGE_COLUMNS", "MERGE_ROWS"). Default: "MERGE_ALL"

**Returns:**
- `spreadsheet_id`: The spreadsheet identifier
- `merged_range`: A1 notation of the merged range
- `merge_type`: Type of merge applied
- `status`: Confirmation of merge operation

**Example:**
```json
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "sheet_name": "Sales Data",
  "range": "A1:D1",
  "merge_type": "MERGE_ALL"
}
```

---

### set_column_width

Set the width of specific columns.

**Parameters:**
- `spreadsheet_id` (string, required): The spreadsheet ID
- `sheet_name` (string, required): Name of the sheet/tab
- `start_column` (integer, required): Starting column index (0-based)
- `end_column` (integer, required): Ending column index (0-based, exclusive)
- `width_pixels` (integer, required): Width in pixels

**Returns:**
- `spreadsheet_id`: The spreadsheet identifier
- `sheet_name`: Name of the sheet
- `start_column`: Starting column index
- `end_column`: Ending column index
- `width_pixels`: Applied width in pixels
- `status`: Confirmation of resize operation

**Example:**
```json
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "sheet_name": "Sales Data",
  "start_column": 0,
  "end_column": 2,
  "width_pixels": 150
}
```

---

### create_chart

Create a chart (bar, line, pie) from data in the spreadsheet.

**Parameters:**
- `spreadsheet_id` (string, required): The spreadsheet ID
- `sheet_name` (string, required): Name of the sheet/tab containing data
- `chart_type` (string, required): Type of chart ("BAR", "COLUMN", "LINE", "PIE")
- `data_range` (string, required): A1 notation range containing chart data
- `title` (string, optional): Chart title
- `x_position` (integer, optional): X position in pixels (default: 100)
- `y_position` (integer, optional): Y position in pixels (default: 100)
- `width` (integer, optional): Chart width in pixels (default: 400)
- `height` (integer, optional): Chart height in pixels (default: 300)

**Returns:**
- `spreadsheet_id`: The spreadsheet identifier
- `chart_id`: Unique identifier for the created chart
- `chart_type`: Type of chart created
- `data_range`: Data range used for the chart
- `position`: Chart position and dimensions
- `status`: Confirmation of chart creation

**Example:**
```json
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "sheet_name": "Sales Data",
  "chart_type": "COLUMN",
  "data_range": "A1:B10",
  "title": "Monthly Sales",
  "x_position": 200,
  "y_position": 150
}
```

## Common Use Cases

### Data Entry and Management
```json
// Create a new spreadsheet
{"title": "Project Budget"}

// Add headers
{
  "spreadsheet_id": "...",
  "sheet_name": "Sheet1",
  "range": "A1:D1",
  "values": [["Item", "Cost", "Quantity", "Total"]]
}

// Add data rows
{
  "spreadsheet_id": "...",
  "sheet_name": "Sheet1",
  "values": [
    ["Laptops", "1200", "5", "6000"],
    ["Software", "500", "10", "5000"]
  ]
}
```

### Professional Formatting
```json
// Format header row
{
  "spreadsheet_id": "...",
  "sheet_name": "Sheet1",
  "range": "A1:D1",
  "background_color": {"red": 0.2, "green": 0.4, "blue": 0.8},
  "text_color": {"red": 1.0, "green": 1.0, "blue": 1.0},
  "bold": true
}

// Format currency columns
{
  "spreadsheet_id": "...",
  "sheet_name": "Sheet1",
  "range": "B:B",
  "number_format": "$#,##0.00"
}
```

### Data Visualization
```json
// Create a chart from data
{
  "spreadsheet_id": "...",
  "sheet_name": "Sheet1",
  "chart_type": "COLUMN",
  "data_range": "A1:D6",
  "title": "Project Costs by Category"
}
```

## Error Handling

Common error scenarios:

- **Invalid spreadsheet_id**: Returns 404 error
- **Sheet not found**: Returns error with available sheet names
- **Invalid range**: Returns error with correct A1 notation format
- **Permission denied**: Check OAuth scope for spreadsheets
- **Invalid format**: Check number format syntax for set_number_format

## Related Tools

- **Drive API**: `search_drive_files` to find spreadsheets
- **Gmail API**: `send_email` to share spreadsheet data
- **Docs API**: For text-based reports and documentation

## Notes

- All ranges use A1 notation (e.g., "A1:B10", "Sheet1!A1:C5")
- Color values are RGB objects with values 0.0-1.0
- Chart positioning uses pixels from top-left corner of sheet
- Number formats follow Google Sheets format syntax
- Maximum chart size is typically 800x600 pixels