"""MCP Server that exposes screen as a resource"""
import asyncio
import base64
import glob
import logging
import json
import os
import sys
from typing import Any, Sequence

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource, 
    Tool, 
    TextContent, 
    ImageContent,
    INVALID_PARAMS,
    INTERNAL_ERROR
)

from src.capture.engine import ScreenCaptureEngine

# Set up logging to both stderr AND a file for debugging with rotation
from logging.handlers import RotatingFileHandler

log_file = os.path.join(os.path.dirname(__file__), '..', 'mcp_server.log')

# Create rotating file handler - max 5MB, keep 2 backup files
file_handler = RotatingFileHandler(
    log_file, 
    mode='a',  # Append mode
    maxBytes=5*1024*1024,  # 5MB max
    backupCount=2,  # Keep 2 old log files
    encoding='utf-8'
)

logging.basicConfig(
    level=logging.INFO,  # Less verbose in production
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),  # CRITICAL: MCP uses stdout for JSON-RPC
        file_handler  # Rotating log file
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Logging to: {log_file} (auto-rotating at 5MB)")


class ScreenMCPServer:
    """MCP Server that provides screen capture as resources and tools"""
    
    def __init__(self):
        """Initialize the MCP server"""
        self.server = Server("screen-access")
        self.capture_engine = ScreenCaptureEngine()
        logger.info("Screen MCP Server initialized")
        logger.info(f"Detected monitors: {self.capture_engine.get_monitor_info()}")
        self._setup_handlers()
    
    def _format_analysis(self, analysis: dict) -> str:
        """Format design analysis into readable text"""
        response = f"""# 🎨 DESIGN ANALYSIS

## 📐 Dimensions: {analysis['dimensions']['width']}x{analysis['dimensions']['height']}px (ratio: {analysis['layout']['aspect_ratio']})

## 🎨 COLOR PALETTE

### Backgrounds
"""
        for color in analysis['colors']['backgrounds'][:3]:
            response += f"• {color['hex']} ({color['percentage']}%)\n"
        
        response += "\n### Text Colors\n"
        for color in analysis['colors']['text_colors'][:3]:
            response += f"• {color['hex']} ({color['percentage']}%)\n"
        
        response += "\n### Accent Colors\n"
        for color in analysis['colors']['accent_colors'][:3]:
            response += f"• {color['hex']} ({color['percentage']}%)\n"
        
        response += f"""
## 📏 LAYOUT
• Container: {analysis['layout']['container_width_estimate']}
• Height: {analysis['layout']['total_height']}px
• Sections: {analysis['layout']['sections_detected']}

## 🔤 TYPOGRAPHY
• Fonts: {', '.join(analysis['typography']['recommendations']['system_fonts'][:2])}
• H1: {analysis['typography']['recommendations']['heading_scale'][0]}
• H2: {analysis['typography']['recommendations']['heading_scale'][1]}
• Body: {analysis['typography']['recommendations']['body_size']}
• Line Height: {analysis['typography']['recommendations']['line_height']['body']}

## 📐 SPACING
• System: {analysis['spacing']['recommendations']['likely_system']}
• Scale: {', '.join(map(str, analysis['spacing']['recommendations']['common_scales'][:6]))}
• Section Padding: {analysis['spacing']['recommendations']['section_padding']}

💡 All design data extracted automatically!
"""
        return response
    
    def _setup_handlers(self):
        """Register MCP protocol handlers"""
        
        # RESOURCES - What screens are available
        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            """Tell MCP what resources we provide"""
            resources = [
                Resource(
                    uri="screen://current",
                    name="Current Screen",
                    mimeType="image/png",
                    description="Live capture of your primary screen - use this to see what the user is working on"
                ),
                Resource(
                    uri="screen://all",
                    name="All Monitors",
                    mimeType="image/png",
                    description="Capture of all monitors combined"
                )
            ]
            
            # Add resource for each monitor
            for monitor in self.capture_engine.get_monitor_info():
                resources.append(
                    Resource(
                        uri=f"screen://monitor/{monitor['id']}",
                        name=f"Monitor {monitor['id']} ({monitor['width']}x{monitor['height']})",
                        mimeType="image/png",
                        description=f"Live capture of monitor {monitor['id']}"
                    )
                )
            
            logger.info(f"Listing {len(resources)} resources")
            return resources
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Handle resource read requests - returns base64 encoded images"""
            logger.info(f"Reading resource: {uri}")
            
            try:
                if uri == "screen://current" or uri == "screen://all":
                    # Capture primary screen
                    png_bytes = self.capture_engine.capture_current()
                    b64_data = base64.b64encode(png_bytes).decode('utf-8')
                    logger.info(f"Captured screen: {len(png_bytes):,} bytes")
                    return f"data:image/png;base64,{b64_data}"
                
                elif uri.startswith("screen://monitor/"):
                    # Extract monitor ID
                    monitor_id = int(uri.split("/")[-1])
                    png_bytes = self.capture_engine.capture_monitor(monitor_id)
                    b64_data = base64.b64encode(png_bytes).decode('utf-8')
                    logger.info(f"Captured monitor {monitor_id}: {len(png_bytes):,} bytes")
                    return f"data:image/png;base64,{b64_data}"
                
                else:
                    raise ValueError(f"Unknown resource: {uri}")
                    
            except Exception as e:
                logger.error(f"Error reading resource {uri}: {e}")
                raise
        
        # TOOLS - Actions Claude can take
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools"""
            try:
                tools = [
                Tool(
                    name="capture_screen",
                    description="""Capture the user's screen with AUTOMATIC comprehensive design analysis.

**AUTOMATICALLY INCLUDES:**
✅ Complete color palette (backgrounds, text, accents with percentages)
✅ Layout structure (sections, container width, dimensions)
✅ Typography recommendations (fonts, sizes, line heights)
✅ Spacing system (8px/4px scale, padding, gaps)
✅ Component detection (nav, hero, sections)
✅ The image itself for visual reference

**ONE tool call = Everything you need to recreate the design!**

Use for:
- UI/UX review and feedback
- Design replication
- Color scheme extraction
- Layout analysis
- Accessibility checks

No need to call multiple tools - this does it ALL automatically.""",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "monitor": {
                                "type": "string",
                                "description": "Which monitor to capture: 'primary', 'all', or monitor number like '1' or '2'",
                                "enum": ["primary", "all", "1", "2"],
                                "default": "primary"
                            },
                            "reason": {
                                "type": "string",
                                "description": "What you're analyzing (e.g., 'checking button spacing', 'color contrast audit', 'layout review')"
                            },
                            "focus_area": {
                                "type": "string",
                                "description": "What aspect to focus on: 'spacing', 'colors', 'typography', 'layout', 'accessibility', 'all'"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="capture_region",
                    description="""Capture a specific region with AUTOMATIC design analysis.

**AUTOMATICALLY INCLUDES:**
✅ Image of the region
✅ Complete color analysis
✅ Layout structure
✅ Typography details
✅ Spacing recommendations

Perfect for analyzing specific UI components (buttons, cards, navbars, forms).
ONE call = Complete component analysis!""",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "x": {
                                "type": "number",
                                "description": "X coordinate of top-left corner"
                            },
                            "y": {
                                "type": "number",
                                "description": "Y coordinate of top-left corner"
                            },
                            "width": {
                                "type": "number",
                                "description": "Width of the region to capture"
                            },
                            "height": {
                                "type": "number",
                                "description": "Height of the region to capture"
                            },
                            "reason": {
                                "type": "string",
                                "description": "What UI element you're inspecting"
                            }
                        },
                        "required": ["x", "y", "width", "height"]
                    }
                ),
                Tool(
                    name="get_monitor_info",
                    description="Get information about all available monitors (resolution, position, etc.). Useful before capturing to know screen dimensions.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="extract_color",
                    description="""Extract color information from a specific point on screen.

Returns hex code, RGB values, HSV values. Perfect for:
- Getting exact color values from designs
- Verifying color implementation
- Building color palettes from screenshots
- Matching colors from reference designs""",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "x": {
                                "type": "number",
                                "description": "X coordinate of the point"
                            },
                            "y": {
                                "type": "number",
                                "description": "Y coordinate of the point"
                            },
                            "sample_size": {
                                "type": "number",
                                "description": "Size of area to sample (NxN pixels, default 5)",
                                "default": 5
                            }
                        },
                        "required": ["x", "y"]
                    }
                ),
                Tool(
                    name="analyze_color_palette",
                    description="""Analyze dominant colors in a screen region.

Extracts the most common colors used in an area. Perfect for:
- Understanding color schemes
- Extracting color palettes from designs
- Analyzing brand colors
- Checking color consistency across UI""",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "x": {
                                "type": "number",
                                "description": "X coordinate of top-left corner"
                            },
                            "y": {
                                "type": "number",
                                "description": "Y coordinate of top-left corner"
                            },
                            "width": {
                                "type": "number",
                                "description": "Width of region to analyze"
                            },
                            "height": {
                                "type": "number",
                                "description": "Height of region to analyze"
                            },
                            "num_colors": {
                                "type": "number",
                                "description": "Number of dominant colors to return (default 5)",
                                "default": 5
                            }
                        },
                        "required": ["x", "y", "width", "height"]
                    }
                ),
                Tool(
                    name="check_contrast",
                    description="""Calculate WCAG contrast ratio between two colors.

Returns contrast ratio and WCAG compliance level. Use for:
- Checking text readability
- Verifying accessibility compliance
- Testing color combinations
- WCAG AA/AAA validation

Ratios:
- 4.5:1 minimum for normal text (WCAG AA)
- 3:1 minimum for large text (WCAG AA)
- 7:1 for normal text (WCAG AAA)""",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "color1_x": {
                                "type": "number",
                                "description": "X coordinate for first color"
                            },
                            "color1_y": {
                                "type": "number",
                                "description": "Y coordinate for first color"
                            },
                            "color2_x": {
                                "type": "number",
                                "description": "X coordinate for second color"
                            },
                            "color2_y": {
                                "type": "number",
                                "description": "Y coordinate for second color"
                            }
                        },
                        "required": ["color1_x", "color1_y", "color2_x", "color2_y"]
                    }
                ),
                Tool(
                    name="capture_active_window",
                    description="""Capture active window with AUTOMATIC design analysis.

**AUTOMATICALLY INCLUDES:**
✅ Window image
✅ Complete color palette
✅ Layout analysis
✅ Typography + spacing

Cleaner than full screen - focuses only on the active application.
ONE call = Complete window analysis!""",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "description": "Why you're capturing this window"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="start_continuous_capture",
                    description="""Continuously capture screen at intervals. Perfect for capturing documentation while scrolling.

Use this when you need to capture content across multiple screens/pages:
- SDK documentation (scroll through while I capture)
- Long articles/tutorials
- Multi-step processes
- Any content that requires scrolling/navigation

I'll take screenshots automatically at your specified interval while you navigate.""",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "duration": {
                                "type": "number",
                                "description": "How long to capture for (in seconds). E.g., 10, 30, 60, 120"
                            },
                            "interval": {
                                "type": "number",
                                "description": "How often to capture (in seconds). E.g., 1, 2, 5",
                                "default": 2
                            },
                            "monitor": {
                                "type": "string",
                                "description": "Which monitor: 'primary', '1', '2'",
                                "default": "primary"
                            },
                            "extract_text": {
                                "type": "boolean",
                                "description": "Extract text from all captures after done? (OCR)",
                                "default": True
                            }
                        },
                        "required": ["duration"]
                    }
                ),
                Tool(
                    name="cleanup_logs",
                    description="Clean up old log files to free disk space. Removes rotated log backups while keeping the current log.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "confirm": {
                                "type": "boolean",
                                "description": "Set to true to confirm cleanup"
                            }
                        },
                        "required": ["confirm"]
                    }
                ),
                Tool(
                    name="analyze_design",
                    description="""COMPREHENSIVE design analysis of a screenshot - extracts EVERYTHING you need to recreate the design.

This is the POWER TOOL for understanding layouts. It automatically extracts:

**COLORS:**
- Background colors (whites, grays, darks)
- Text colors (primary, secondary, muted)
- Accent colors (buttons, links, highlights)
- Complete dominant color palette with percentages

**LAYOUT:**
- Section structure (hero, features, CTA, etc.)
- Container width estimates
- Vertical sections breakdown
- Aspect ratio and dimensions

**TYPOGRAPHY:**
- Recommended font families (system fonts)
- Heading size scale estimates
- Body text size recommendations
- Line height guidelines

**COMPONENTS:**
- Navigation detection
- Hero section identification  
- Card/grid layouts
- Button styles and patterns

**SPACING:**
- Spacing scale system (8px or 4px)
- Section padding estimates
- Element gap recommendations

Use this BEFORE creating templates to get the full design DNA.""",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "monitor": {
                                "type": "string",
                                "description": "Which monitor to analyze: 'primary', '1', '2'",
                                "default": "primary"
                            },
                            "x": {
                                "type": "number",
                                "description": "Optional: X coordinate to analyze specific region only"
                            },
                            "y": {
                                "type": "number",
                                "description": "Optional: Y coordinate to analyze specific region only"
                            },
                            "width": {
                                "type": "number",
                                "description": "Optional: Width of region to analyze"
                            },
                            "height": {
                                "type": "number",
                                "description": "Optional: Height of region to analyze"
                            }
                        },
                        "required": []
                    }
                )
                ]
                logger.info(f"Returning {len(tools)} tools to MCP client")
                return tools
            except Exception as e:
                logger.error(f"ERROR in list_tools(): {e}", exc_info=True)
                return []
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent]:
            """Handle tool calls"""
            logger.info(f"Tool called: {name} with args: {arguments}")
            
            try:
                if name == "capture_screen":
                    monitor = arguments.get("monitor", "primary")
                    reason = arguments.get("reason", "User requested")
                    
                    logger.info(f"Capturing screen: {monitor} - Reason: {reason}")
                    
                    # Capture based on monitor selection
                    if monitor == "primary" or monitor == "1":
                        png_bytes = self.capture_engine.capture_current()
                    elif monitor == "all":
                        png_bytes = self.capture_engine.capture_current()
                    elif monitor.isdigit():
                        png_bytes = self.capture_engine.capture_monitor(int(monitor))
                    else:
                        png_bytes = self.capture_engine.capture_current()
                    
                    # Return as ImageContent
                    b64_data = base64.b64encode(png_bytes).decode('utf-8')
                    
                    return [
                        ImageContent(
                            type="image",
                            data=b64_data,
                            mimeType="image/png"
                        ),
                        TextContent(
                            type="text",
                            text=f"Screen captured: {len(png_bytes):,} bytes\n\n✅ Image ready for analysis"
                        )
                    ]
                
                elif name == "capture_region":
                    x = int(arguments.get("x", 0))
                    y = int(arguments.get("y", 0))
                    width = int(arguments.get("width", 800))
                    height = int(arguments.get("height", 600))
                    reason = arguments.get("reason", "UI element inspection")
                    
                    logger.info(f"Capturing region: x={x}, y={y}, w={width}, h={height} - Reason: {reason}")
                    
                    png_bytes = self.capture_engine.capture_region(x, y, width, height)
                    b64_data = base64.b64encode(png_bytes).decode('utf-8')
                    
                    return [
                        ImageContent(
                            type="image",
                            data=b64_data,
                            mimeType="image/png"
                        ),
                        TextContent(
                            type="text",
                            text=f"Region captured: ({x}, {y}) {width}x{height}px\n\n✅ Image ready for analysis"
                        )
                    ]
                
                elif name == "get_monitor_info":
                    monitor_info = self.capture_engine.get_monitor_info()
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(monitor_info, indent=2)
                        )
                    ]
                
                elif name == "extract_color":
                    x = int(arguments.get("x", 0))
                    y = int(arguments.get("y", 0))
                    sample_size = int(arguments.get("sample_size", 5))
                    
                    logger.info(f"Extracting color at ({x}, {y})")
                    
                    color_info = self.capture_engine.extract_color_at_point(x, y, sample_size)
                    
                    # Format response
                    response = f"""Color at ({x}, {y}):
                    
**Hex:** {color_info['hex']}
**RGB:** R: {color_info['rgb']['r']}, G: {color_info['rgb']['g']}, B: {color_info['rgb']['b']}
**HSV:** H: {color_info['hsv']['h']}°, S: {color_info['hsv']['s']}%, V: {color_info['hsv']['v']}%

Sample size: {sample_size}x{sample_size} pixels"""
                    
                    return [
                        TextContent(
                            type="text",
                            text=response
                        )
                    ]
                
                elif name == "analyze_color_palette":
                    x = int(arguments.get("x", 0))
                    y = int(arguments.get("y", 0))
                    width = int(arguments.get("width", 100))
                    height = int(arguments.get("height", 100))
                    num_colors = int(arguments.get("num_colors", 5))
                    
                    logger.info(f"Analyzing color palette in region ({x}, {y}) {width}x{height}")
                    
                    palette_info = self.capture_engine.analyze_colors_in_region(x, y, width, height, num_colors)
                    
                    # Format response
                    response = f"""Color Palette Analysis
Region: ({x}, {y}) - {width}x{height}px
Total unique colors: {palette_info['total_unique_colors']}

**Dominant Colors:**
"""
                    for i, color in enumerate(palette_info['dominant_colors'], 1):
                        response += f"\n{i}. {color['hex']} (RGB: {color['rgb']['r']}, {color['rgb']['g']}, {color['rgb']['b']}) - {color['percentage']}%"
                    
                    return [
                        TextContent(
                            type="text",
                            text=response
                        )
                    ]
                
                elif name == "check_contrast":
                    x1 = int(arguments.get("color1_x", 0))
                    y1 = int(arguments.get("color1_y", 0))
                    x2 = int(arguments.get("color2_x", 0))
                    y2 = int(arguments.get("color2_y", 0))
                    
                    logger.info(f"Checking contrast between ({x1}, {y1}) and ({x2}, {y2})")
                    
                    # Extract both colors
                    color1_info = self.capture_engine.extract_color_at_point(x1, y1)
                    color2_info = self.capture_engine.extract_color_at_point(x2, y2)
                    
                    # Calculate contrast
                    color1_rgb = (color1_info['rgb']['r'], color1_info['rgb']['g'], color1_info['rgb']['b'])
                    color2_rgb = (color2_info['rgb']['r'], color2_info['rgb']['g'], color2_info['rgb']['b'])
                    
                    contrast_ratio = self.capture_engine.calculate_contrast_ratio(color1_rgb, color2_rgb)
                    
                    # Determine WCAG compliance
                    aa_normal = "✅ PASS" if contrast_ratio >= 4.5 else "❌ FAIL"
                    aa_large = "✅ PASS" if contrast_ratio >= 3.0 else "❌ FAIL"
                    aaa_normal = "✅ PASS" if contrast_ratio >= 7.0 else "❌ FAIL"
                    
                    response = f"""Contrast Analysis

**Color 1** ({x1}, {y1}): {color1_info['hex']}
**Color 2** ({x2}, {y2}): {color2_info['hex']}

**Contrast Ratio:** {contrast_ratio:.2f}:1

**WCAG Compliance:**
- Normal Text (AA): {aa_normal} (requires 4.5:1)
- Large Text (AA): {aa_large} (requires 3:1)
- Normal Text (AAA): {aaa_normal} (requires 7:1)

Recommendation: {"Great contrast! Meets all accessibility standards." if contrast_ratio >= 7.0 else "Consider increasing contrast for better readability." if contrast_ratio < 4.5 else "Good contrast for most use cases."}"""
                    
                    return [
                        TextContent(
                            type="text",
                            text=response
                        )
                    ]
                
                elif name == "capture_active_window":
                    reason = arguments.get("reason", "Capturing active window")
                    
                    logger.info(f"Capturing active window - Reason: {reason}")
                    
                    png_bytes = self.capture_engine.capture_active_window()
                    b64_data = base64.b64encode(png_bytes).decode('utf-8')
                    
                    return [
                        ImageContent(
                            type="image",
                            data=b64_data,
                            mimeType="image/png"
                        ),
                        TextContent(
                            type="text",
                            text=f"Active window captured: {len(png_bytes):,} bytes\n\n✅ Image ready for analysis"
                        )
                    ]
                
                elif name == "start_continuous_capture":
                    duration = int(arguments.get("duration", 30))
                    interval = float(arguments.get("interval", 2))
                    monitor_str = arguments.get("monitor", "primary")
                    extract_text = arguments.get("extract_text", True)
                    
                    # Parse monitor
                    if monitor_str == "primary" or monitor_str == "1":
                        monitor = 1
                    elif monitor_str == "2":
                        monitor = 2
                    else:
                        monitor = 1
                    
                    logger.info(f"Starting continuous capture: {duration}s duration, {interval}s interval, monitor {monitor}")
                    
                    # Capture frames (await since it's now async)
                    captures = await self.capture_engine.continuous_capture(duration, interval, monitor)
                    
                    logger.info(f"Captured {len(captures)} frames")
                    
                    # Extract text if requested
                    if extract_text:
                        logger.info("Extracting text from all captures...")
                        all_text = []
                        
                        for i, capture_bytes in enumerate(captures, 1):
                            text = self.capture_engine.extract_text_from_image(capture_bytes)
                            if text and not text.startswith("[OCR Error"):
                                all_text.append(f"=== Frame {i}/{len(captures)} ===\n{text}\n")
                        
                        combined_text = "\n".join(all_text)
                        
                        return [
                            TextContent(
                                type="text",
                                text=f"""Continuous capture complete!

**Captured:** {len(captures)} frames over {duration} seconds
**Interval:** Every {interval} seconds
**Monitor:** {monitor}

**Extracted Text:**
{combined_text if combined_text else "[No text detected or OCR not installed]"}

Note: Install 'easyocr' or 'pytesseract' for text extraction.
"""
                            )
                        ]
                    else:
                        # Just return capture info without text
                        return [
                            TextContent(
                                type="text",
                                text=f"""Continuous capture complete!

**Captured:** {len(captures)} frames over {duration} seconds
**Interval:** Every {interval} seconds  
**Monitor:** {monitor}

Text extraction disabled. Set extract_text=true to enable OCR."""
                            )
                        ]
                
                elif name == "cleanup_logs":
                    confirm = arguments.get("confirm", False)
                    
                    if not confirm:
                        return [
                            TextContent(
                                type="text",
                                text="Cleanup not confirmed. Set 'confirm' to true to proceed."
                            )
                        ]
                    
                    # Find and remove old log backups
                    log_dir = os.path.dirname(log_file)
                    log_backups = glob.glob(os.path.join(log_dir, "mcp_server.log.*"))
                    
                    removed_count = 0
                    freed_space = 0
                    
                    for backup in log_backups:
                        try:
                            size = os.path.getsize(backup)
                            os.remove(backup)
                            removed_count += 1
                            freed_space += size
                            logger.info(f"Removed log backup: {backup}")
                        except Exception as e:
                            logger.error(f"Failed to remove {backup}: {e}")
                    
                    # Also check for test capture images
                    test_images = glob.glob(os.path.join(log_dir, "test_capture*.png"))
                    for img in test_images:
                        try:
                            size = os.path.getsize(img)
                            os.remove(img)
                            removed_count += 1
                            freed_space += size
                            logger.info(f"Removed test image: {img}")
                        except Exception as e:
                            logger.error(f"Failed to remove {img}: {e}")
                    
                    freed_mb = freed_space / (1024 * 1024)
                    
                    return [
                        TextContent(
                            type="text",
                            text=f"Cleanup complete!\n- Removed {removed_count} file(s)\n- Freed {freed_mb:.2f} MB disk space\n\nNote: All screenshots are captured in-memory only and never saved to disk."
                        )
                    ]
                
                elif name == "analyze_design":
                    monitor = arguments.get("monitor", "primary")
                    x = arguments.get("x")
                    y = arguments.get("y")
                    width = arguments.get("width")
                    height = arguments.get("height")
                    
                    logger.info(f"Analyzing design: monitor={monitor}, region={x},{y},{width}x{height}")
                    
                    # Capture the screen or region
                    if x is not None and y is not None and width and height:
                        # Analyze specific region
                        png_bytes = self.capture_engine.capture_region(int(x), int(y), int(width), int(height))
                    else:
                        # Analyze full screen
                        if monitor == "primary" or monitor == "1":
                            png_bytes = self.capture_engine.capture_current()
                        elif monitor == "2":
                            png_bytes = self.capture_engine.capture_monitor(2)
                        else:
                            png_bytes = self.capture_engine.capture_current()
                    
                    # Run comprehensive analysis
                    analysis = self.capture_engine.analyze_comprehensive_design(png_bytes)
                    
                    # Format the response nicely
                    response = f"""# 🎨 COMPREHENSIVE DESIGN ANALYSIS

## 📐 Dimensions
- **Width:** {analysis['dimensions']['width']}px
- **Height:** {analysis['dimensions']['height']}px
- **Aspect Ratio:** {analysis['layout']['aspect_ratio']}

## 🎨 Color Palette

### Background Colors
"""
                    for color in analysis['colors']['backgrounds']:
                        response += f"\n- **{color['hex']}** - {color['percentage']}% of design"
                    
                    response += "\n\n### Text Colors"
                    for color in analysis['colors']['text_colors']:
                        response += f"\n- **{color['hex']}** - {color['percentage']}%"
                    
                    response += "\n\n### Accent Colors (Buttons, Links)"
                    for color in analysis['colors']['accent_colors']:
                        response += f"\n- **{color['hex']}** - {color['percentage']}%"
                    
                    response += "\n\n### All Dominant Colors"
                    for color in analysis['colors']['all_dominant']:
                        response += f"\n- {color['hex']} ({color['percentage']}%)"
                    
                    response += f"""

## 📏 Layout Structure
- **Container Width:** {analysis['layout']['container_width_estimate']}
- **Total Height:** {analysis['layout']['total_height']}px
- **Sections Detected:** {analysis['layout']['sections_detected']}

### Vertical Section Breakdown
"""
                    for section in analysis['layout']['sections'][:5]:  # Show first 5
                        response += f"\n- Section {section['position']}: Y {section['y_range'][0]}-{section['y_range'][1]}px (brightness: {section['avg_brightness']})"
                    
                    response += f"""

## 🔤 Typography Recommendations
{analysis['typography']['note']}

### Recommended Fonts
{', '.join(analysis['typography']['recommendations']['system_fonts'])}

### Size Scale
- **H1:** {analysis['typography']['recommendations']['heading_scale'][0]}
- **H2:** {analysis['typography']['recommendations']['heading_scale'][1]}
- **H3:** {analysis['typography']['recommendations']['heading_scale'][2]}
- **Body:** {analysis['typography']['recommendations']['body_size']}

### Line Heights
- **Headings:** {analysis['typography']['recommendations']['line_height']['headings']}
- **Body:** {analysis['typography']['recommendations']['line_height']['body']}

### Text Regions Detected
{len(analysis['typography']['estimated_text_regions'])} regions with text-like patterns

## 🧩 Components Detected
{analysis['components']['note']}

### Navigation
- Detected: {analysis['components']['estimated_components']['navigation']['detected']}
- Position: {analysis['components']['estimated_components']['navigation']['likely_position']}
- Height: {analysis['components']['estimated_components']['navigation']['height_estimate']}

### Hero Section
- Position: {analysis['components']['estimated_components']['hero_section']['position']}
- Est. Height: {analysis['components']['estimated_components']['hero_section']['estimated_height']}

## 📐 Spacing System
{analysis['spacing']['note']}

- **Base System:** {analysis['spacing']['recommendations']['likely_system']}
- **Scale:** {', '.join(map(str, analysis['spacing']['recommendations']['common_scales']))}
- **Section Padding:** {analysis['spacing']['recommendations']['section_padding']}
- **Element Gaps:** {analysis['spacing']['recommendations']['element_gaps']}

---
**Analysis Version:** {analysis['analysis_version']}

💡 **Tip:** Use this data to create pixel-perfect recreations of the design!
"""
                    
                    return [
                        TextContent(
                            type="text",
                            text=response
                        )
                    ]
                
                else:
                    raise ValueError(f"Unknown tool: {name}")
                    
            except Exception as e:
                logger.error(f"Error calling tool {name}: {e}")
                return [
                    TextContent(
                        type="text",
                        text=f"Error: {str(e)}"
                    )
                ]
        
        # PROMPTS - Pre-built prompts for common tasks
        @self.server.list_prompts()
        async def list_prompts():
            """List available prompts"""
            return [
                {
                    "name": "review_ui",
                    "description": "Comprehensive UI/UX review - spacing, colors, typography, layout, consistency",
                    "arguments": []
                },
                {
                    "name": "check_accessibility",
                    "description": "WCAG compliance audit - contrast, text size, focus states, screen reader support",
                    "arguments": []
                },
                {
                    "name": "quick_design_check",
                    "description": "Quick check for common design issues - alignment, spacing, visual hierarchy",
                    "arguments": []
                },
                {
                    "name": "color_analysis",
                    "description": "Analyze color usage, contrast ratios, and color accessibility",
                    "arguments": []
                }
            ]
        
        @self.server.get_prompt()
        async def get_prompt(name: str, arguments: dict):
            """Get a specific prompt"""
            if name == "review_ui":
                return {
                    "messages": [
                        {
                            "role": "user",
                            "content": """Capture and analyze my screen for UI/UX issues. Check:

SPACING & LAYOUT:
- Inconsistent padding/margins
- Alignment issues
- Cramped or excessive whitespace
- Grid/column alignment

TYPOGRAPHY:
- Font sizes and readability
- Line height and spacing
- Hierarchy (headings vs body)
- Text contrast

COLORS:
- Color contrast ratios
- Consistent use of colors
- Visual hierarchy through color

COMPONENTS:
- Button sizes and states
- Form field consistency
- Interactive element feedback
- Component alignment

Provide specific, actionable feedback with measurements where possible."""
                        }
                    ]
                }
            elif name == "check_accessibility":
                return {
                    "messages": [
                        {
                            "role": "user",
                            "content": """Capture and audit my screen for accessibility (WCAG 2.1 AA):

COLOR & CONTRAST:
- Text contrast ratios (4.5:1 minimum for normal text, 3:1 for large)
- UI component contrast (3:1 minimum)
- Color not sole indicator

TEXT & CONTENT:
- Text size (minimum 16px body text recommended)
- Line height (1.5 minimum for body text)
- Text spacing and readability

INTERACTIVE ELEMENTS:
- Focus indicators visible and clear
- Touch targets (44x44px minimum)
- Button/link text clarity

Rate issues by severity:
🔴 Critical - Blocks users
🟡 Important - Impacts usability  
🟢 Minor - Nice to have

Provide specific fixes for each issue."""
                        }
                    ]
                }
            elif name == "quick_design_check":
                return {
                    "messages": [
                        {
                            "role": "user",
                            "content": """Quick design check of my screen. Focus on:

1. **Alignment** - Are elements properly aligned?
2. **Spacing** - Is spacing consistent (8px grid recommended)?
3. **Visual Hierarchy** - Clear distinction between primary/secondary/tertiary?
4. **Consistency** - Are similar elements styled the same?

Give me top 3-5 issues to fix immediately."""
                        }
                    ]
                }
            elif name == "color_analysis":
                return {
                    "messages": [
                        {
                            "role": "user",
                            "content": """Analyze the colors in my UI:

1. **Color Palette** - What colors are being used?
2. **Contrast Ratios** - Check WCAG compliance for text/bg combinations
3. **Color Meaning** - Are colors used consistently (e.g., red for errors)?
4. **Accessibility** - Any issues for colorblind users?
5. **Recommendations** - Suggest improvements

Focus on measuring actual contrast ratios where possible."""
                        }
                    ]
                }
            else:
                raise ValueError(f"Unknown prompt: {name}")
    
    async def run(self):
        """Start the MCP server"""
        logger.info("Starting MCP Screen Server...")
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Entry point"""
    try:
        logger.info("=" * 60)
        logger.info("MCP Screen Server Starting...")
        logger.info("=" * 60)
        server = ScreenMCPServer()
        await server.run()
    except Exception as e:
        logger.error(f"FATAL ERROR in main(): {e}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"FATAL ERROR: {e}", exc_info=True)
        sys.exit(1)

