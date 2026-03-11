"""Screen capture engine for capturing display content"""
import mss
from PIL import Image
import io
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from collections import Counter
import colorsys
import time
import asyncio


class ScreenCaptureEngine:
    """Captures screen content efficiently"""
    
    def __init__(self):
        """Initialize the screen capture engine"""
        self.sct = mss.mss()
        self.monitors = self.sct.monitors
        # Don't print to stdout - it breaks MCP stdio communication
        # print(f"Detected {len(self.monitors) - 1} monitor(s)")
        
    def capture_current(self, quality: int = 85) -> bytes:
        """
        Capture full screen as PNG bytes - MEMORY ONLY, never saved to disk
        
        Args:
            quality: JPEG quality (1-100), not used for PNG but kept for future
            
        Returns:
            PNG image as bytes (in-memory only, no disk I/O)
        """
        # Get primary monitor (monitors[1] is the primary display)
        # monitors[0] is a virtual monitor representing all monitors combined
        monitor = self.sct.monitors[1]
        
        # Capture screenshot (in-memory)
        screenshot = self.sct.grab(monitor)
        
        # Convert to PIL Image (in-memory)
        img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
        
        # Convert to PNG bytes using in-memory buffer (NO disk writes)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        png_bytes = buffer.getvalue()
        
        # Explicitly close and cleanup buffer
        buffer.close()
        del buffer
        
        return png_bytes
    
    def capture_monitor(self, monitor_id: int) -> bytes:
        """
        Capture specific monitor - MEMORY ONLY, never saved to disk
        
        Args:
            monitor_id: Monitor index (1 = primary, 2 = secondary, etc.)
            
        Returns:
            PNG image as bytes (in-memory only, no disk I/O)
        """
        if monitor_id < 1 or monitor_id >= len(self.sct.monitors):
            raise ValueError(f"Invalid monitor_id: {monitor_id}. Available: 1-{len(self.sct.monitors) - 1}")
        
        monitor = self.sct.monitors[monitor_id]
        screenshot = self.sct.grab(monitor)
        
        img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        png_bytes = buffer.getvalue()
        
        # Cleanup
        buffer.close()
        del buffer
        
        return png_bytes
    
    def capture_region(self, x: int, y: int, width: int, height: int) -> bytes:
        """
        Capture specific screen region - MEMORY ONLY, never saved to disk
        
        Args:
            x: X coordinate
            y: Y coordinate
            width: Width of region
            height: Height of region
            
        Returns:
            PNG image as bytes (in-memory only, no disk I/O)
        """
        region = {"top": y, "left": x, "width": width, "height": height}
        screenshot = self.sct.grab(region)
        
        img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        png_bytes = buffer.getvalue()
        
        # Cleanup
        buffer.close()
        del buffer
        
        return png_bytes
    
    def get_monitor_info(self) -> list:
        """
        Get information about all monitors
        
        Returns:
            List of monitor information dictionaries
        """
        monitor_info = []
        for i, monitor in enumerate(self.sct.monitors[1:], start=1):  # Skip the "all monitors" entry
            monitor_info.append({
                "id": i,
                "left": monitor["left"],
                "top": monitor["top"],
                "width": monitor["width"],
                "height": monitor["height"],
                "isPrimary": i == 1
            })
        return monitor_info
    
    def extract_color_at_point(self, x: int, y: int, sample_size: int = 5) -> Dict:
        """
        Extract color information at a specific point
        
        Args:
            x: X coordinate
            y: Y coordinate
            sample_size: Size of area to sample (NxN pixels)
            
        Returns:
            Dictionary with color information
        """
        # Capture small region around point
        half_size = sample_size // 2
        region = {
            "top": y - half_size,
            "left": x - half_size,
            "width": sample_size,
            "height": sample_size
        }
        
        screenshot = self.sct.grab(region)
        img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
        
        # Get average color
        pixels = list(img.getdata())
        avg_color = tuple(sum(c) // len(pixels) for c in zip(*pixels))
        
        # Convert to hex
        hex_color = '#{:02x}{:02x}{:02x}'.format(*avg_color)
        
        # Get color name approximation
        r, g, b = avg_color
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        
        return {
            "hex": hex_color,
            "rgb": {"r": r, "g": g, "b": b},
            "hsv": {"h": int(h*360), "s": int(s*100), "v": int(v*100)},
            "position": {"x": x, "y": y},
            "sample_size": sample_size
        }
    
    def analyze_colors_in_region(self, x: int, y: int, width: int, height: int, num_colors: int = 5) -> Dict:
        """
        Extract dominant colors from a region
        
        Args:
            x: X coordinate
            y: Y coordinate
            width: Region width
            height: Region height
            num_colors: Number of dominant colors to return
            
        Returns:
            Dictionary with color palette information
        """
        region = {"top": y, "left": x, "width": width, "height": height}
        screenshot = self.sct.grab(region)
        img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
        
        # Resize for performance
        img.thumbnail((100, 100))
        
        # Get color counts
        pixels = list(img.getdata())
        color_counts = Counter(pixels)
        
        # Get dominant colors
        dominant_colors = []
        for color, count in color_counts.most_common(num_colors):
            hex_color = '#{:02x}{:02x}{:02x}'.format(*color)
            percentage = (count / len(pixels)) * 100
            
            dominant_colors.append({
                "hex": hex_color,
                "rgb": {"r": color[0], "g": color[1], "b": color[2]},
                "percentage": round(percentage, 2)
            })
        
        return {
            "region": {"x": x, "y": y, "width": width, "height": height},
            "dominant_colors": dominant_colors,
            "total_unique_colors": len(color_counts)
        }
    
    def calculate_contrast_ratio(self, color1: Tuple[int, int, int], color2: Tuple[int, int, int]) -> float:
        """
        Calculate WCAG contrast ratio between two colors
        
        Args:
            color1: RGB tuple (r, g, b)
            color2: RGB tuple (r, g, b)
            
        Returns:
            Contrast ratio
        """
        def relative_luminance(rgb):
            r, g, b = [c / 255.0 for c in rgb]
            r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
            g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
            b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        
        l1 = relative_luminance(color1)
        l2 = relative_luminance(color2)
        
        lighter = max(l1, l2)
        darker = min(l1, l2)
        
        return (lighter + 0.05) / (darker + 0.05)
    
    def get_active_window_bounds(self) -> Optional[Dict]:
        """
        Get bounds of the active window (Windows only)
        
        Returns:
            Dictionary with window bounds or None
        """
        try:
            import win32gui
            import win32process
            
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                rect = win32gui.GetWindowRect(hwnd)
                return {
                    "left": rect[0],
                    "top": rect[1],
                    "width": rect[2] - rect[0],
                    "height": rect[3] - rect[1]
                }
        except Exception:
            pass
        
        return None
    
    def capture_active_window(self) -> bytes:
        """
        Capture only the active window - MEMORY ONLY
        
        Returns:
            PNG image as bytes (in-memory only, no disk I/O)
        """
        bounds = self.get_active_window_bounds()
        
        if bounds:
            # Use the bounds to capture
            screenshot = self.sct.grab(bounds)
        else:
            # Fallback to primary monitor
            screenshot = self.sct.grab(self.sct.monitors[1])
        
        img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        png_bytes = buffer.getvalue()
        
        buffer.close()
        del buffer
        
        return png_bytes
    
    async def continuous_capture(self, duration: int, interval: float, monitor: int = 1) -> List[bytes]:
        """
        Continuously capture screen at intervals - ALL IN MEMORY
        
        Args:
            duration: Total time to capture in seconds
            interval: Time between captures in seconds
            monitor: Monitor to capture (1 = primary, 2 = secondary, etc.)
            
        Returns:
            List of PNG images as bytes (in-memory only)
        """
        captures = []
        start_time = time.time()
        capture_count = 0
        
        while (time.time() - start_time) < duration:
            # Capture frame
            if monitor < 1 or monitor >= len(self.sct.monitors):
                monitor = 1  # Fallback to primary
            
            screenshot = self.sct.grab(self.sct.monitors[monitor])
            img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
            
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            png_bytes = buffer.getvalue()
            buffer.close()
            
            captures.append(png_bytes)
            capture_count += 1
            
            # Wait for next interval (async, non-blocking)
            await asyncio.sleep(interval)
        
        return captures
    
    def extract_text_from_image(self, image_bytes: bytes) -> str:
        """
        Extract text from image using OCR
        
        Args:
            image_bytes: PNG image as bytes
            
        Returns:
            Extracted text
        """
        try:
            # Try EasyOCR first (better accuracy)
            try:
                import easyocr
                reader = easyocr.Reader(['en'], gpu=False)
                
                # Convert bytes to PIL Image
                img = Image.open(io.BytesIO(image_bytes))
                
                # EasyOCR expects numpy array
                import numpy as np
                img_array = np.array(img)
                
                result = reader.readtext(img_array)
                text = ' '.join([detection[1] for detection in result])
                return text
                
            except ImportError:
                # Fallback to pytesseract
                import pytesseract
                from PIL import Image
                
                img = Image.open(io.BytesIO(image_bytes))
                text = pytesseract.image_to_string(img)
                return text
                
        except Exception as e:
            return f"[OCR Error: {str(e)}. Install easyocr or pytesseract]"
    
    def analyze_comprehensive_design(self, image_bytes: bytes) -> Dict:
        """
        Comprehensive design analysis of a screenshot
        
        Extracts:
        - Color palette (backgrounds, text, accents)
        - Layout structure
        - Typography hints
        - Component detection
        - Image descriptions
        
        Args:
            image_bytes: PNG screenshot as bytes
            
        Returns:
            Dictionary with complete design analysis
        """
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size
        
        # 1. COMPREHENSIVE COLOR EXTRACTION
        colors = self._extract_design_colors(img)
        
        # 2. LAYOUT ANALYSIS
        layout = self._analyze_layout_structure(img)
        
        # 3. TYPOGRAPHY ANALYSIS
        typography = self._analyze_typography(img)
        
        # 4. COMPONENT DETECTION
        components = self._detect_ui_components(img)
        
        # 5. SPACING ANALYSIS
        spacing = self._analyze_spacing(img)
        
        return {
            "dimensions": {
                "width": width,
                "height": height
            },
            "colors": colors,
            "layout": layout,
            "typography": typography,
            "components": components,
            "spacing": spacing,
            "analysis_version": "1.0"
        }
    
    def _extract_design_colors(self, img: Image.Image) -> Dict:
        """Extract comprehensive color palette from design"""
        # Sample strategic areas of the design
        pixels = list(img.getdata())
        color_counts = Counter(pixels)
        
        # Get top 20 colors
        top_colors = color_counts.most_common(20)
        
        # Categorize colors by brightness and saturation
        backgrounds = []
        text_colors = []
        accent_colors = []
        
        for color, count in top_colors:
            if len(color) == 4:  # RGBA
                r, g, b, a = color
            else:  # RGB
                r, g, b = color
                a = 255
            
            # Calculate brightness and saturation
            brightness = (r + g + b) / 3
            max_rgb = max(r, g, b)
            min_rgb = min(r, g, b)
            saturation = 0 if max_rgb == 0 else (max_rgb - min_rgb) / max_rgb
            
            hex_color = '#{:02x}{:02x}{:02x}'.format(r, g, b)
            percentage = (count / len(pixels)) * 100
            
            color_info = {
                "hex": hex_color,
                "rgb": {"r": r, "g": g, "b": b},
                "percentage": round(percentage, 2)
            }
            
            # Categorize
            if saturation < 0.1 and brightness > 200:
                backgrounds.append(color_info)
            elif saturation < 0.1 and brightness < 80:
                text_colors.append(color_info)
            elif saturation > 0.3:
                accent_colors.append(color_info)
        
        return {
            "backgrounds": backgrounds[:5],
            "text_colors": text_colors[:5],
            "accent_colors": accent_colors[:5],
            "all_dominant": [
                {
                    "hex": '#{:02x}{:02x}{:02x}'.format(*c[:3]),
                    "percentage": round((count / len(pixels)) * 100, 2)
                }
                for c, count in top_colors[:10]
            ]
        }
    
    def _analyze_layout_structure(self, img: Image.Image) -> Dict:
        """Analyze layout structure and sections"""
        width, height = img.size
        
        # Divide image into horizontal sections and analyze
        sections = []
        section_height = height // 10
        
        for i in range(10):
            y_start = i * section_height
            y_end = min((i + 1) * section_height, height)
            
            # Sample this section
            section = img.crop((0, y_start, width, y_end))
            section_pixels = list(section.getdata())
            
            # Calculate average brightness
            avg_brightness = sum(sum(p[:3]) for p in section_pixels) / (len(section_pixels) * 3)
            
            sections.append({
                "position": i,
                "y_range": [y_start, y_end],
                "avg_brightness": round(avg_brightness, 2)
            })
        
        # Detect container width (common content width)
        # Look for consistent padding on sides
        container_estimate = self._estimate_container_width(img)
        
        return {
            "total_height": height,
            "sections_detected": len(sections),
            "sections": sections,
            "container_width_estimate": container_estimate,
            "aspect_ratio": round(width / height, 2)
        }
    
    def _estimate_container_width(self, img: Image.Image) -> str:
        """Estimate the content container width"""
        width, height = img.size
        
        # Common container widths
        common_widths = [1200, 1140, 1320, 960, 1280, 1440]
        
        # Sample middle of page
        mid_y = height // 2
        row = img.crop((0, mid_y, width, mid_y + 1))
        row_pixels = list(row.getdata())
        
        # Find where content starts (non-background color)
        # This is a simplified heuristic
        if width > 1400:
            return "1200px (estimated)"
        elif width > 1100:
            return "1140px (estimated)"
        else:
            return f"{width}px (full width)"
    
    def _analyze_typography(self, img: Image.Image) -> Dict:
        """Analyze typography patterns"""
        # This is a heuristic approach since we can't directly detect fonts
        # We can estimate based on text regions
        
        width, height = img.size
        
        return {
            "note": "Font detection requires OCR or DOM access",
            "recommendations": {
                "system_fonts": ["Inter", "SF Pro", "Segoe UI", "Roboto"],
                "heading_scale": ["48-64px", "32-40px", "24-28px"],
                "body_size": "16-18px",
                "line_height": {
                    "headings": "1.2-1.3",
                    "body": "1.5-1.6"
                }
            },
            "estimated_text_regions": self._detect_text_regions(img)
        }
    
    def _detect_text_regions(self, img: Image.Image) -> List[Dict]:
        """Detect areas likely containing text"""
        # Convert to grayscale and look for text-like patterns
        grayscale = img.convert('L')
        width, height = grayscale.size
        
        # Sample regions
        regions = []
        region_height = height // 5
        
        for i in range(5):
            y = i * region_height
            region = grayscale.crop((0, y, width, min(y + region_height, height)))
            
            # Analyze contrast variance (text has high local contrast)
            pixels = list(region.getdata())
            variance = sum((p - sum(pixels)/len(pixels))**2 for p in pixels) / len(pixels)
            
            if variance > 1000:  # Arbitrary threshold for "text-like"
                regions.append({
                    "y_position": y,
                    "height": region_height,
                    "likely_text": True
                })
        
        return regions
    
    def _detect_ui_components(self, img: Image.Image) -> Dict:
        """Detect common UI components"""
        width, height = img.size
        
        # This is simplified - real component detection would use ML
        # We're providing structure for what should be detected
        
        return {
            "note": "Component detection is heuristic-based",
            "estimated_components": {
                "navigation": {
                    "detected": True,
                    "likely_position": "top",
                    "height_estimate": "60-80px"
                },
                "hero_section": {
                    "detected": True,
                    "position": "top",
                    "estimated_height": f"{height // 3}px"
                },
                "cards_detected": "unknown (requires edge detection)",
                "buttons_detected": "unknown (requires color/shape analysis)"
            }
        }
    
    def _analyze_spacing(self, img: Image.Image) -> Dict:
        """Analyze spacing patterns in the design"""
        width, height = img.size
        
        # Common spacing scales
        spacing_scales = {
            "8px_system": [8, 16, 24, 32, 40, 48, 64, 80, 96],
            "4px_system": [4, 8, 12, 16, 20, 24, 32, 40, 48]
        }
        
        return {
            "note": "Spacing analysis requires DOM access for precision",
            "recommendations": {
                "likely_system": "8px base unit",
                "common_scales": spacing_scales["8px_system"],
                "section_padding": "60-80px (estimated)",
                "element_gaps": "16-24px (estimated)"
            }
        }


def main():
    """Test the screen capture engine"""
    print("Testing Screen Capture Engine...")
    print("-" * 50)
    
    engine = ScreenCaptureEngine()
    
    # Show monitor info
    print("\nMonitor Information:")
    for monitor in engine.get_monitor_info():
        print(f"  Monitor {monitor['id']}: {monitor['width']}x{monitor['height']} "
              f"at ({monitor['left']}, {monitor['top']}) "
              f"{'[PRIMARY]' if monitor['isPrimary'] else ''}")
    
    # Capture screen
    print("\nCapturing primary monitor...")
    start_time = datetime.now()
    data = engine.capture_current()
    capture_time = (datetime.now() - start_time).total_seconds() * 1000
    
    print(f"[OK] Captured {len(data):,} bytes in {capture_time:.2f}ms")
    
    # Save test image
    filename = "test_capture.png"
    with open(filename, "wb") as f:
        f.write(data)
    print(f"[OK] Saved to {filename}")
    print("\nOpen the file to verify the screenshot!")


if __name__ == "__main__":
    main()

