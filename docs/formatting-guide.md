# Formatting Capabilities Guide

Comprehensive guide to the rich formatting capabilities across Google Workspace services.

## Overview

The Google Workspace MCP server now includes **48 formatting and styling tools** across Gmail, Docs, Sheets, and Slides, enabling professional document creation and visual communication.

### What's New in Version 0.1.29

- **Rich Text Formatting**: Apply bold, italic, underline, colors, and fonts
- **Advanced Cell Formatting**: Professional spreadsheet styling and charts
- **Email Formatting**: Create HTML emails with rich content
- **Presentation Design**: Custom layouts, backgrounds, and visual elements

## Cross-Service Formatting Examples

### Professional Email with Formatting

Create visually appealing HTML emails with structured content:

```python
# 1. Format the email content with HTML styling
format_email_content(
    content="Welcome to our Q4 Business Review",
    bold_text=["Welcome", "Q4 Business Review"],
    italic_text=["Business Review"],
    underline_text=["Q4"],
    text_color="#2E5BBA"
)

# 2. Create a formatted email with rich content
create_formatted_email(
    to="stakeholders@company.com",
    subject="Q4 2024 Business Review - Key Insights",
    body_html="""
    <h2 style="color: #2E5BBA;">Q4 Performance Summary</h2>
    <p><strong>Revenue Growth:</strong> <span style="color: #28A745;">+25%</span></p>
    <p><strong>New Markets:</strong> Expanded to <em>5 new regions</em></p>
    <p style="background-color: #F8F9FA; padding: 10px; border-left: 4px solid #2E5BBA;">
        <strong>Next Steps:</strong> Review the attached presentation for detailed analysis.
    </p>
    """,
    attachments=["Q4-Report.pdf"]
)

# 3. Set a professional email signature
set_email_signature(
    signature_html="""
    <div style="font-family: Arial, sans-serif; color: #666;">
        <strong>John Smith</strong><br>
        <em>VP of Operations</em><br>
        Company Inc. | <a href="mailto:john@company.com">john@company.com</a>
    </div>
    """
)
```

### Document with Rich Formatting and Structure

Create professional documents with headings, formatted text, and tables:

```python
# 1. Create document with structured content
document_id = create_document(title="Q4 Business Analysis")

# 2. Apply heading styles for structure
apply_heading_style(
    document_id=document_id,
    heading_text="Executive Summary",
    heading_level=1  # H1 style
)

# 3. Format key text with emphasis
format_text_in_document(
    document_id=document_id,
    start_index=50,
    end_index=75,
    bold=True,
    font_size=14,
    text_color={"red": 0.2, "green": 0.4, "blue": 0.8},
    font_family="Roboto"
)

# 4. Format paragraph alignment and spacing
format_paragraph_in_document(
    document_id=document_id,
    start_index=100,
    end_index=300,
    alignment="LEFT",
    line_spacing=1.5,
    space_above=10,
    space_below=10
)

# 5. Create a structured list
create_list_in_document(
    document_id=document_id,
    insertion_index=400,
    list_items=[
        "Revenue increased by 25% year-over-year",
        "Customer acquisition improved by 40%",
        "Operational efficiency gains of 15%"
    ],
    list_type="BULLETED"  # or "NUMBERED"
)

# 6. Insert a data table
insert_table_in_document(
    document_id=document_id,
    insertion_index=500,
    rows=4,
    columns=3,
    table_data=[
        ["Metric", "Q3 2024", "Q4 2024"],
        ["Revenue", "$2.4M", "$3.0M"],
        ["Customers", "1,200", "1,680"],
        ["Growth Rate", "18%", "25%"]
    ]
)

# 7. Set professional document margins
set_document_margins(
    document_id=document_id,
    top_margin=72,    # 1 inch
    bottom_margin=72,
    left_margin=90,   # 1.25 inches
    right_margin=90
)
```

### Professional Spreadsheet with Charts

Create data-driven spreadsheets with formatting and visualizations:

```python
# 1. Create spreadsheet with data
spreadsheet_id = create_spreadsheet(title="Q4 Performance Dashboard")

# 2. Add structured data
update_sheet_values(
    spreadsheet_id=spreadsheet_id,
    sheet_name="Dashboard",
    range="A1:D6",
    values=[
        ["Month", "Revenue", "Customers", "Growth %"],
        ["October", "950000", "1200", "18"],
        ["November", "1100000", "1350", "20"],
        ["December", "1300000", "1680", "25"],
        ["Total Q4", "3350000", "4230", "Average: 21"]
    ]
)

# 3. Format header row professionally
format_cells(
    spreadsheet_id=spreadsheet_id,
    sheet_name="Dashboard",
    range="A1:D1",
    background_color={"red": 0.2, "green": 0.4, "blue": 0.8},
    text_color={"red": 1.0, "green": 1.0, "blue": 1.0},
    bold=True,
    font_size=12
)

# 4. Apply currency formatting
set_number_format(
    spreadsheet_id=spreadsheet_id,
    sheet_name="Dashboard",
    range="B2:B5",
    number_format="$#,##0"
)

# 5. Apply percentage formatting
set_number_format(
    spreadsheet_id=spreadsheet_id,
    sheet_name="Dashboard",
    range="D2:D4",
    number_format="0%"
)

# 6. Merge and format totals row
merge_cells(
    spreadsheet_id=spreadsheet_id,
    sheet_name="Dashboard",
    range="A5:A5",
    merge_type="MERGE_ALL"
)

format_cells(
    spreadsheet_id=spreadsheet_id,
    sheet_name="Dashboard",
    range="A5:D5",
    bold=True,
    background_color={"red": 0.9, "green": 0.9, "blue": 0.95}
)

# 7. Set optimal column widths
set_column_width(
    spreadsheet_id=spreadsheet_id,
    sheet_name="Dashboard",
    start_column=0,  # Column A
    end_column=4,    # Columns A-D
    width_pixels=120
)

# 8. Create a revenue trend chart
create_chart(
    spreadsheet_id=spreadsheet_id,
    sheet_name="Dashboard",
    chart_type="COLUMN",
    data_range="A1:B4",
    title="Q4 Monthly Revenue",
    x_position=300,
    y_position=100,
    width=400,
    height=250
)

# 9. Create a customer growth chart
create_chart(
    spreadsheet_id=spreadsheet_id,
    sheet_name="Dashboard",
    chart_type="LINE",
    data_range="A1:C4",
    title="Revenue vs Customer Growth",
    x_position=300,
    y_position=400,
    width=400,
    height=250
)
```

### Dynamic Presentation with Rich Content

Create engaging presentations with formatted text, images, and layouts:

```python
# 1. Create presentation
presentation_id = create_presentation(title="Q4 2024 Business Review")

# 2. Create title slide with custom formatting
title_slide_id = add_slide(
    presentation_id=presentation_id,
    layout="TITLE",
    insertion_index=0
)

add_formatted_text_box(
    presentation_id=presentation_id,
    slide_id=title_slide_id,
    text="Q4 2024 Business Review",
    x_pt=50,
    y_pt=150,
    width_pt=620,
    height_pt=100,
    font_size=48,
    font_family="Roboto",
    bold=True,
    text_color={"red": 0.2, "green": 0.4, "blue": 0.8}
)

add_formatted_text_box(
    presentation_id=presentation_id,
    slide_id=title_slide_id,
    text="Exceptional Performance & Strategic Growth",
    x_pt=50,
    y_pt=280,
    width_pt=620,
    height_pt=60,
    font_size=24,
    italic=True,
    text_color={"red": 0.4, "green": 0.4, "blue": 0.4}
)

# 3. Set professional slide background
set_slide_background(
    presentation_id=presentation_id,
    slide_id=title_slide_id,
    background_color={"red": 0.98, "green": 0.98, "blue": 1.0}
)

# 4. Create key metrics slide with bulleted content
metrics_slide_id = create_bulleted_list_slide(
    presentation_id=presentation_id,
    title="Key Performance Metrics",
    bullet_points=[
        "Revenue Growth: +25% ($3.35M total)",
        "Customer Base: +40% (4,230 customers)",
        "Market Expansion: 5 new regions",
        "Customer Satisfaction: 98% (industry-leading)"
    ],
    insertion_index=1
)

# 5. Add data visualization
add_image(
    presentation_id=presentation_id,
    slide_id=metrics_slide_id,
    image_url="https://example.com/revenue-chart.png",
    x_pt=400,
    y_pt=200,
    width_pt=280,
    height_pt=200
)

# 6. Create comparison slide with two-column layout
comparison_slide_id = add_slide(
    presentation_id=presentation_id,
    layout="TITLE_AND_TWO_COLUMNS",
    insertion_index=2
)

# Format title with specific styling
format_text_in_slide(
    presentation_id=presentation_id,
    shape_id="title_shape_id",  # Retrieved from slide structure
    start_index=0,
    end_index=20,
    font_size=32,
    bold=True,
    text_color={"red": 0.2, "green": 0.4, "blue": 0.8}
)

# 7. Add call-to-action slide
cta_slide_id = add_slide(
    presentation_id=presentation_id,
    layout="BIG_NUMBER",
    insertion_index=3
)

add_formatted_text_box(
    presentation_id=presentation_id,
    slide_id=cta_slide_id,
    text="Ready for 2025 Growth",
    x_pt=100,
    y_pt=200,
    width_pt=520,
    height_pt=80,
    font_size=36,
    bold=True,
    text_color={"red": 0.2, "green": 0.7, "blue": 0.3},
    background_color={"red": 0.95, "green": 1.0, "blue": 0.95}
)
```

## Integration Workflows

### Claude Desktop Automation Example

```typescript
// Example Claude Desktop conversation flow
"Create a quarterly business report with the following requirements:

1. **Professional Email Announcement**
   - Send to all stakeholders
   - Include formatted summary with key metrics
   - Attach the full report

2. **Comprehensive Document**
   - Executive summary with heading styles
   - Formatted data tables
   - Professional margins and typography

3. **Data Dashboard**
   - Monthly performance spreadsheet
   - Revenue and customer growth charts
   - Professional formatting with corporate colors

4. **Executive Presentation**
   - Title slide with brand styling
   - Key metrics with bullet points
   - Visual charts and call-to-action

Could you create all of these connected documents with consistent formatting?"
```

### Automated Workflow Integration

```python
# Complete workflow for quarterly reporting
def create_quarterly_report(quarter, year, metrics_data):
    """
    Automated workflow to create complete quarterly business report
    with consistent formatting across all Google Workspace services.
    """

    # 1. Create data dashboard in Sheets
    spreadsheet_id = create_formatted_dashboard(metrics_data)

    # 2. Generate charts and export URLs
    chart_urls = create_performance_charts(spreadsheet_id, metrics_data)

    # 3. Create comprehensive document
    doc_id = create_formatted_document(quarter, year, metrics_data)

    # 4. Build executive presentation
    presentation_id = create_executive_presentation(
        quarter, year, metrics_data, chart_urls
    )

    # 5. Send formatted email announcement
    send_quarterly_announcement(
        quarter, year, doc_id, presentation_id, spreadsheet_id
    )

    return {
        "dashboard_url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
        "report_url": f"https://docs.google.com/document/d/{doc_id}",
        "presentation_url": f"https://docs.google.com/presentation/d/{presentation_id}",
        "status": "Complete quarterly report package created"
    }

def create_formatted_dashboard(data):
    """Create professionally formatted Sheets dashboard"""
    # Implementation using format_cells, create_chart, etc.
    pass

def create_formatted_document(quarter, year, data):
    """Create structured document with rich formatting"""
    # Implementation using format_text_in_document, apply_heading_style, etc.
    pass

def create_executive_presentation(quarter, year, data, charts):
    """Create visual presentation with formatting"""
    # Implementation using add_formatted_text_box, set_slide_background, etc.
    pass

def send_quarterly_announcement(quarter, year, doc_id, pres_id, sheet_id):
    """Send formatted email with links to all documents"""
    # Implementation using create_formatted_email
    pass
```

## Formatting Best Practices

### Color Schemes and Branding

```python
# Corporate brand colors (RGB 0.0-1.0)
BRAND_COLORS = {
    "primary_blue": {"red": 0.2, "green": 0.4, "blue": 0.8},
    "success_green": {"red": 0.2, "green": 0.7, "blue": 0.3},
    "warning_orange": {"red": 1.0, "green": 0.6, "blue": 0.0},
    "error_red": {"red": 0.8, "green": 0.2, "blue": 0.2},
    "neutral_gray": {"red": 0.4, "green": 0.4, "blue": 0.4},
    "light_background": {"red": 0.98, "green": 0.98, "blue": 1.0}
}

# Typography hierarchy
FONT_SIZES = {
    "heading_1": 36,
    "heading_2": 28,
    "heading_3": 22,
    "body_large": 16,
    "body_normal": 14,
    "body_small": 12,
    "caption": 10
}

# Professional spacing (in points)
SPACING = {
    "page_margins": 72,      # 1 inch
    "paragraph_spacing": 12,  # Space between paragraphs
    "line_height_normal": 1.5,
    "section_spacing": 24    # Space between sections
}
```

### Responsive Design Considerations

```python
# Standard document sizes and positioning
SLIDE_DIMENSIONS = {
    "width": 720,   # Standard slide width in points
    "height": 540,  # Standard slide height in points
    "safe_margin": 50  # Safe margin from edges
}

DOC_LAYOUT = {
    "standard_width": 612,  # 8.5 inches in points
    "margins": {
        "top": 72,     # 1 inch
        "bottom": 72,
        "left": 90,    # 1.25 inches for binding
        "right": 90
    }
}

SHEET_FORMATTING = {
    "header_height": 25,        # Header row height in pixels
    "column_width_default": 100, # Default column width
    "chart_size_small": {"width": 300, "height": 200},
    "chart_size_large": {"width": 500, "height": 350}
}
```

## Error Handling and Troubleshooting

### Common Issues and Solutions

**Color Format Errors:**
```python
# ❌ Incorrect (0-255 values)
{"red": 255, "green": 128, "blue": 0}

# ✅ Correct (0.0-1.0 values)
{"red": 1.0, "green": 0.5, "blue": 0.0}
```

**Position and Size Errors:**
```python
# ❌ Text box outside slide bounds
add_text_box(x_pt=800, y_pt=600, width_pt=200, height_pt=100)  # Extends beyond 720×540

# ✅ Properly positioned within slide
add_text_box(x_pt=50, y_pt=50, width_pt=620, height_pt=100)   # Within bounds
```

**Number Format Issues:**
```python
# ❌ Invalid number format
set_number_format(number_format="currency")

# ✅ Valid Google Sheets format syntax
set_number_format(number_format="$#,##0.00")
```

### Validation Helpers

```python
def validate_rgb_color(color_obj):
    """Validate RGB color object format"""
    required_keys = {"red", "green", "blue"}
    if not isinstance(color_obj, dict) or not required_keys.issubset(color_obj.keys()):
        raise ValueError("Color must be dict with 'red', 'green', 'blue' keys")

    for key, value in color_obj.items():
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"Color {key} must be between 0.0 and 1.0, got {value}")

    return True

def validate_slide_position(x_pt, y_pt, width_pt, height_pt, slide_width=720, slide_height=540):
    """Validate element position within slide bounds"""
    if x_pt + width_pt > slide_width:
        raise ValueError(f"Element extends beyond slide width: {x_pt + width_pt} > {slide_width}")

    if y_pt + height_pt > slide_height:
        raise ValueError(f"Element extends beyond slide height: {y_pt + height_pt} > {slide_height}")

    return True
```

## Advanced Automation Use Cases

### Multi-Document Report Generation

Create interconnected documents with consistent formatting:

1. **Data Collection**: Gather metrics from various sources
2. **Spreadsheet Dashboard**: Create formatted data tables and charts
3. **Executive Document**: Generate structured report with references
4. **Presentation**: Build visual summary with key insights
5. **Email Distribution**: Send formatted announcement with links

### Brand Consistency Automation

Implement brand guidelines across all documents:

1. **Style Templates**: Define consistent color schemes and typography
2. **Automated Formatting**: Apply brand styles to new documents
3. **Quality Checks**: Validate formatting against brand standards
4. **Cross-Platform Consistency**: Ensure alignment across Docs, Sheets, and Slides

### Dynamic Content Updates

Create living documents that update automatically:

1. **Data Refresh**: Update spreadsheet data from external sources
2. **Chart Regeneration**: Automatically update visualizations
3. **Document Updates**: Refresh report sections with new data
4. **Presentation Sync**: Update slide content to match latest data

This formatting guide demonstrates the comprehensive capabilities for creating professional, branded content across all Google Workspace services with rich visual styling and consistent design.