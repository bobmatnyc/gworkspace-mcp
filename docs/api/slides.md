# Google Slides API

Google Slides tools for presentation creation, content management, and formatting.

**21 tools available**

## Overview

The Google Slides integration provides comprehensive presentation functionality including:

- **Presentation Management**: Create, read, list presentations
- **Slide Operations**: Add, delete, update slides
- **Content Creation**: Add text boxes, images, formatted content
- **Text Formatting**: Apply fonts, colors, styles to text
- **Layout Management**: Apply layouts, backgrounds, positioning
- **Advanced Features**: Bulleted lists, custom layouts

## Authentication Required

All Slides tools require authentication with the following scope:
- `https://www.googleapis.com/auth/presentations`

## Tools

### create_presentation

Create a new Google Slides presentation.

**Parameters:**
- `title` (string, required): Title for the new presentation

**Returns:**
- `presentation_id`: Unique identifier for the created presentation
- `title`: Presentation title
- `url`: Direct link to open the presentation
- `status`: Creation status

**Example:**
```json
{
  "title": "Q4 2024 Business Review"
}
```

---

### get_presentation

Get presentation metadata and structure.

**Parameters:**
- `presentation_id` (string, required): The presentation ID

**Returns:**
- `presentation_id`: The presentation identifier
- `title`: Presentation title
- `page_size`: Dimensions of slides
- `slides`: Array of slide metadata
- `masters`: Layout masters available

**Example:**
```json
{
  "presentation_id": "1EAYk18WDjIG-zp_0vLm3CsfQh_i8eXc67Jo2O9C6Vuc"
}
```

---

### list_presentations

List presentations accessible to the user.

**Parameters:**
- `page_size` (integer, optional): Maximum number of presentations to return (default: 10)

**Returns:**
- `presentations`: Array of presentation summaries
- `total_count`: Total number of presentations found

**Example:**
```json
{
  "page_size": 20
}
```

---

### get_presentation_text

Extract all text content from a presentation.

**Parameters:**
- `presentation_id` (string, required): The presentation ID

**Returns:**
- `presentation_id`: The presentation identifier
- `title`: Presentation title
- `slide_count`: Number of slides
- `slides`: Array with text content per slide
- `combined_text`: All text combined with slide markers

**Example:**
```json
{
  "presentation_id": "1EAYk18WDjIG-zp_0vLm3CsfQh_i8eXc67Jo2O9C6Vuc"
}
```

---

### get_slide

Get content and structure of a specific slide.

**Parameters:**
- `presentation_id` (string, required): The presentation ID
- `slide_id` (string, required): The slide ID

**Returns:**
- `presentation_id`: The presentation identifier
- `slide_id`: The slide identifier
- `slide_index`: Position in presentation
- `layout`: Applied layout information
- `elements`: Array of page elements (text boxes, images, etc.)

**Example:**
```json
{
  "presentation_id": "1EAYk18WDjIG-zp_0vLm3CsfQh_i8eXc67Jo2O9C6Vuc",
  "slide_id": "g2162a7b9e5_0_0"
}
```

---

### add_slide

Add a new slide to the presentation.

**Parameters:**
- `presentation_id` (string, required): The presentation ID
- `layout` (string, optional): Predefined layout ("BLANK", "CAPTION_ONLY", "TITLE", "TITLE_AND_BODY", "TITLE_AND_TWO_COLUMNS", "TITLE_ONLY", "SECTION_HEADER", "SECTION_TITLE_AND_DESCRIPTION", "ONE_COLUMN_TEXT", "MAIN_POINT", "BIG_NUMBER"). Default: "BLANK"
- `insertion_index` (integer, optional): Position to insert slide (0-based)

**Returns:**
- `presentation_id`: The presentation identifier
- `slide_id`: ID of the created slide
- `layout`: Applied layout
- `insertion_index`: Position where slide was inserted
- `status`: Creation status

**Example:**
```json
{
  "presentation_id": "1EAYk18WDjIG-zp_0vLm3CsfQh_i8eXc67Jo2O9C6Vuc",
  "layout": "TITLE_AND_BODY",
  "insertion_index": 1
}
```

---

### delete_slide

Delete a slide from the presentation.

**Parameters:**
- `presentation_id` (string, required): The presentation ID
- `slide_id` (string, required): The slide ID to delete

**Returns:**
- `presentation_id`: The presentation identifier
- `slide_id`: ID of the deleted slide
- `status`: Deletion confirmation

**Example:**
```json
{
  "presentation_id": "1EAYk18WDjIG-zp_0vLm3CsfQh_i8eXc67Jo2O9C6Vuc",
  "slide_id": "g2162a7b9e5_0_5"
}
```

---

### update_slide_text

Update text in an existing shape on a slide.

**Parameters:**
- `presentation_id` (string, required): The presentation ID
- `shape_id` (string, required): ID of the text shape to update
- `text` (string, required): New text content

**Returns:**
- `presentation_id`: The presentation identifier
- `shape_id`: ID of the updated shape
- `text_length`: Length of the new text
- `status`: Update confirmation

**Example:**
```json
{
  "presentation_id": "1EAYk18WDjIG-zp_0vLm3CsfQh_i8eXc67Jo2O9C6Vuc",
  "shape_id": "g2162a7b9e5_0_1",
  "text": "Updated slide content with new information"
}
```

---

### format_text_in_slide

Apply formatting to specific text ranges in a slide.

**Parameters:**
- `presentation_id` (string, required): The presentation ID
- `shape_id` (string, required): ID of the text shape
- `start_index` (integer, required): Starting character position (0-based)
- `end_index` (integer, required): Ending character position (exclusive)
- `bold` (boolean, optional): Apply bold formatting
- `italic` (boolean, optional): Apply italic formatting
- `underline` (boolean, optional): Apply underline formatting
- `font_size` (integer, optional): Font size in points
- `font_family` (string, optional): Font family name
- `text_color` (object, optional): RGB color object

**Returns:**
- `presentation_id`: The presentation identifier
- `shape_id`: ID of the formatted shape
- `formatted_range`: Character range that was formatted
- `applied_formatting`: Summary of formatting applied
- `status`: Formatting confirmation

**Example:**
```json
{
  "presentation_id": "1EAYk18WDjIG-zp_0vLm3CsfQh_i8eXc67Jo2O9C6Vuc",
  "shape_id": "g2162a7b9e5_0_1",
  "start_index": 0,
  "end_index": 15,
  "bold": true,
  "font_size": 24,
  "text_color": {"red": 0.2, "green": 0.4, "blue": 0.8}
}
```

---

### add_formatted_text_box

Add a text box with custom formatting to a slide.

**Parameters:**
- `presentation_id` (string, required): The presentation ID
- `slide_id` (string, required): The slide ID
- `text` (string, required): Text content
- `x_pt` (number, optional): X position in points (default: 100)
- `y_pt` (number, optional): Y position in points (default: 100)
- `width_pt` (number, optional): Width in points (default: 300)
- `height_pt` (number, optional): Height in points (default: 50)
- `font_size` (integer, optional): Font size in points
- `font_family` (string, optional): Font family name
- `text_color` (object, optional): RGB color object
- `background_color` (object, optional): RGB background color object
- `bold` (boolean, optional): Apply bold formatting
- `italic` (boolean, optional): Apply italic formatting

**Returns:**
- `presentation_id`: The presentation identifier
- `slide_id`: The slide identifier
- `text_box_id`: ID of the created text box
- `text_length`: Length of the text
- `position`: Position and size information
- `status`: Creation status

**Example:**
```json
{
  "presentation_id": "1EAYk18WDjIG-zp_0vLm3CsfQh_i8eXc67Jo2O9C6Vuc",
  "slide_id": "g2162a7b9e5_0_0",
  "text": "Key Performance Metrics",
  "x_pt": 50,
  "y_pt": 50,
  "width_pt": 400,
  "height_pt": 80,
  "font_size": 28,
  "bold": true,
  "text_color": {"red": 0.1, "green": 0.3, "blue": 0.7}
}
```

---

### add_text_box

Add a basic text box to a slide.

**Parameters:**
- `presentation_id` (string, required): The presentation ID
- `slide_id` (string, required): The slide ID
- `text` (string, required): Text content
- `x_pt` (number, optional): X position in points (default: 100)
- `y_pt` (number, optional): Y position in points (default: 100)
- `width_pt` (number, optional): Width in points (default: 300)
- `height_pt` (number, optional): Height in points (default: 50)

**Returns:**
- `presentation_id`: The presentation identifier
- `slide_id`: The slide identifier
- `text_box_id`: ID of the created text box
- `text_length`: Length of the text
- `position`: Position and size information
- `status`: Creation status

**Example:**
```json
{
  "presentation_id": "1EAYk18WDjIG-zp_0vLm3CsfQh_i8eXc67Jo2O9C6Vuc",
  "slide_id": "g2162a7b9e5_0_0",
  "text": "Additional notes and comments",
  "x_pt": 100,
  "y_pt": 300
}
```

---

### set_slide_background

Set the background color or image for a slide.

**Parameters:**
- `presentation_id` (string, required): The presentation ID
- `slide_id` (string, required): The slide ID
- `background_color` (object, optional): RGB color object for solid background
- `image_url` (string, optional): URL of image for background (mutually exclusive with color)

**Returns:**
- `presentation_id`: The presentation identifier
- `slide_id`: The slide identifier
- `background_type`: Type of background applied ("color" or "image")
- `status`: Update confirmation

**Example (Color Background):**
```json
{
  "presentation_id": "1EAYk18WDjIG-zp_0vLm3CsfQh_i8eXc67Jo2O9C6Vuc",
  "slide_id": "g2162a7b9e5_0_0",
  "background_color": {"red": 0.95, "green": 0.95, "blue": 1.0}
}
```

**Example (Image Background):**
```json
{
  "presentation_id": "1EAYk18WDjIG-zp_0vLm3CsfQh_i8eXc67Jo2O9C6Vuc",
  "slide_id": "g2162a7b9e5_0_0",
  "image_url": "https://example.com/background-image.jpg"
}
```

---

### create_bulleted_list_slide

Create a slide with a bulleted list layout.

**Parameters:**
- `presentation_id` (string, required): The presentation ID
- `title` (string, required): Slide title
- `bullet_points` (array, required): Array of bullet point text strings
- `insertion_index` (integer, optional): Position to insert slide

**Returns:**
- `presentation_id`: The presentation identifier
- `slide_id`: ID of the created slide
- `title`: Applied title
- `bullet_count`: Number of bullet points added
- `insertion_index`: Position where slide was inserted
- `status`: Creation status

**Example:**
```json
{
  "presentation_id": "1EAYk18WDjIG-zp_0vLm3CsfQh_i8eXc67Jo2O9C6Vuc",
  "title": "Key Achievements",
  "bullet_points": [
    "Increased revenue by 25%",
    "Launched 3 new products",
    "Expanded to 5 new markets",
    "Improved customer satisfaction to 98%"
  ],
  "insertion_index": 2
}
```

---

### apply_slide_layout

Apply a predefined layout to an existing slide.

**Parameters:**
- `presentation_id` (string, required): The presentation ID
- `slide_id` (string, required): The slide ID
- `layout` (string, required): Layout to apply ("BLANK", "CAPTION_ONLY", "TITLE", "TITLE_AND_BODY", etc.)

**Returns:**
- `presentation_id`: The presentation identifier
- `slide_id`: The slide identifier
- `layout`: Applied layout
- `status`: Layout application confirmation

**Available Layouts:**
- `BLANK`: Empty slide
- `TITLE`: Title slide
- `TITLE_AND_BODY`: Title with content area
- `TITLE_AND_TWO_COLUMNS`: Title with two-column content
- `TITLE_ONLY`: Title only
- `SECTION_HEADER`: Section header
- `CAPTION_ONLY`: Caption only
- `BIG_NUMBER`: Large number display

**Example:**
```json
{
  "presentation_id": "1EAYk18WDjIG-zp_0vLm3CsfQh_i8eXc67Jo2O9C6Vuc",
  "slide_id": "g2162a7b9e5_0_0",
  "layout": "TITLE_AND_TWO_COLUMNS"
}
```

---

### add_image

Add an image to a slide from a URL.

**Parameters:**
- `presentation_id` (string, required): The presentation ID
- `slide_id` (string, required): The slide ID
- `image_url` (string, required): URL of the image to add
- `x_pt` (number, optional): X position in points (default: 100)
- `y_pt` (number, optional): Y position in points (default: 100)
- `width_pt` (number, optional): Width in points (default: 300)
- `height_pt` (number, optional): Height in points (default: 200)

**Returns:**
- `presentation_id`: The presentation identifier
- `slide_id`: The slide identifier
- `image_id`: ID of the created image element
- `image_url`: URL of the added image
- `position`: Position and size information
- `status`: Creation status

**Example:**
```json
{
  "presentation_id": "1EAYk18WDjIG-zp_0vLm3CsfQh_i8eXc67Jo2O9C6Vuc",
  "slide_id": "g2162a7b9e5_0_0",
  "image_url": "https://example.com/chart.png",
  "x_pt": 200,
  "y_pt": 150,
  "width_pt": 400,
  "height_pt": 250
}
```

## Common Use Cases

### Creating a Professional Presentation
```json
// 1. Create presentation
{"title": "Q4 Business Review"}

// 2. Add title slide
{
  "presentation_id": "...",
  "layout": "TITLE",
  "insertion_index": 0
}

// 3. Add formatted title
{
  "presentation_id": "...",
  "slide_id": "...",
  "text": "Q4 2024 Business Review",
  "font_size": 36,
  "bold": true,
  "text_color": {"red": 0.1, "green": 0.3, "blue": 0.7}
}
```

### Content-Rich Slides
```json
// Create bulleted list slide
{
  "presentation_id": "...",
  "title": "Key Achievements",
  "bullet_points": [
    "Revenue growth: 25%",
    "New markets: 5 regions",
    "Customer satisfaction: 98%"
  ]
}

// Add supporting chart
{
  "presentation_id": "...",
  "slide_id": "...",
  "image_url": "https://charts.example.com/revenue-growth.png",
  "x_pt": 400,
  "y_pt": 200
}
```

### Visual Customization
```json
// Set slide background
{
  "presentation_id": "...",
  "slide_id": "...",
  "background_color": {"red": 0.98, "green": 0.98, "blue": 1.0}
}

// Format text with brand colors
{
  "presentation_id": "...",
  "shape_id": "...",
  "start_index": 0,
  "end_index": 20,
  "font_family": "Roboto",
  "font_size": 28,
  "text_color": {"red": 0.2, "green": 0.4, "blue": 0.8}
}
```

## Positioning and Sizing

All position and size values use **points** (pt) as the unit:
- 1 inch = 72 points
- Standard slide size: 720pt × 540pt (10" × 7.5")
- Origin (0,0) is top-left corner

**Common Positioning:**
- Header area: `y_pt: 50-100`
- Content area: `y_pt: 150-400`
- Footer area: `y_pt: 450-500`
- Left margin: `x_pt: 50-100`
- Right content: `x_pt: 400-600`

## Color Format

Colors use RGB objects with values from 0.0 to 1.0:
```json
{
  "red": 0.2,    // 20% red
  "green": 0.4,  // 40% green
  "blue": 0.8    // 80% blue
}
```

**Common Brand Colors:**
- Corporate Blue: `{"red": 0.2, "green": 0.4, "blue": 0.8}`
- Success Green: `{"red": 0.2, "green": 0.7, "blue": 0.3}`
- Warning Orange: `{"red": 1.0, "green": 0.6, "blue": 0.0}`
- Error Red: `{"red": 0.8, "green": 0.2, "blue": 0.2}`

## Error Handling

Common error scenarios:

- **Invalid presentation_id**: Returns 404 error
- **Slide not found**: Returns error with available slide IDs
- **Invalid layout**: Returns error with supported layout options
- **Image URL inaccessible**: Returns error with URL validation
- **Permission denied**: Check OAuth scope for presentations
- **Invalid positioning**: Check that coordinates are within slide bounds

## Related Tools

- **Drive API**: `search_drive_files` to find presentations
- **Gmail API**: `send_email` to share presentation links
- **Sheets API**: `create_chart` for data visualization in slides
- **Docs API**: For detailed content creation and formatting

## Notes

- Slide dimensions are typically 720pt × 540pt (standard widescreen)
- Image URLs must be publicly accessible or from Google Drive
- Text formatting applies to character ranges within text elements
- Layout changes may affect existing content positioning
- Maximum image size recommendations: 800pt × 600pt
- Font families should be web-safe fonts or Google Fonts