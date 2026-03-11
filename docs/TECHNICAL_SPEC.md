# MCP Screen Access Server - Technical Specification

## 🏗️ System Architecture

### High-Level Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                     Cursor IDE / Claude                      │
│                    (MCP Client)                              │
└────────────────────────┬────────────────────────────────────┘
                         │ MCP Protocol (stdio/HTTP)
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  MCP Screen Server                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              MCP Protocol Handler                     │   │
│  │  - Resource endpoints                                 │   │
│  │  - Tool endpoints                                     │   │
│  │  - Prompt templates                                   │   │
│  └────────────┬─────────────────────────────────────────┘   │
│               │                                              │
│  ┌────────────▼─────────────────────────────────────────┐   │
│  │           Screen Capture Engine                       │   │
│  │  - Display monitoring                                 │   │
│  │  - Change detection                                   │   │
│  │  - Window tracking                                    │   │
│  │  - Region capture                                     │   │
│  └────────────┬─────────────────────────────────────────┘   │
│               │                                              │
│  ┌────────────▼─────────────────────────────────────────┐   │
│  │           Privacy & Security Layer                    │   │
│  │  - App whitelist/blacklist                            │   │
│  │  - Sensitive region masking                           │   │
│  │  - Pause controls                                     │   │
│  └────────────┬─────────────────────────────────────────┘   │
│               │                                              │
│  ┌────────────▼─────────────────────────────────────────┐   │
│  │              Cache & History                          │   │
│  │  - Screen state history                               │   │
│  │  - Delta compression                                  │   │
│  │  - Semantic deduplication                             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   Operating System   │
              │   Screen APIs        │
              │  (Win32/X11/Cocoa)   │
              └──────────────────────┘
```

## 📦 Component Breakdown

### 1. MCP Protocol Handler

**Responsibilities:**
- Implements MCP server protocol
- Exposes resources, tools, and prompts
- Handles JSON-RPC communication
- Manages client connections

**Implementation:**
```python
# Uses official MCP Python SDK
from mcp.server import Server
from mcp.server.stdio import stdio_server

class ScreenMCPServer:
    def __init__(self):
        self.server = Server("screen-access")
        self.capture_engine = ScreenCaptureEngine()
        self.privacy_layer = PrivacyLayer()
        self.cache = ScreenCache()
        
    async def start(self):
        # Register resources
        self.server.list_resources(self.list_resources)
        self.server.read_resource(self.read_resource)
        
        # Register tools
        self.server.list_tools(self.list_tools)
        self.server.call_tool(self.call_tool)
        
        # Start server
        async with stdio_server() as (read, write):
            await self.server.run(read, write)
```

### 2. Screen Capture Engine

**Responsibilities:**
- Capture screen content efficiently
- Monitor for changes
- Track active windows
- Support multi-monitor setups

**Platform Support:**
- **Windows**: Win32 API (BitBlt, DXGI Desktop Duplication)
- **macOS**: CGDisplayCreateImage
- **Linux**: X11/Wayland screenshot APIs

**Implementation Strategy:**
```python
class ScreenCaptureEngine:
    def __init__(self):
        self.monitors = self._detect_monitors()
        self.active_window_tracker = ActiveWindowTracker()
        self.change_detector = ChangeDetector()
        
    def capture_current(self) -> ScreenCapture:
        """Capture current screen state"""
        
    def capture_window(self, window_id: str) -> ScreenCapture:
        """Capture specific window"""
        
    def capture_region(self, x, y, w, h) -> ScreenCapture:
        """Capture specific region"""
        
    def detect_changes(self) -> bool:
        """Check if screen has changed since last capture"""
```

**Libraries:**
- **Primary**: `mss` (fast, cross-platform)
- **Windows Optimization**: `pywin32` for DXGI Desktop Duplication API
- **Window Detection**: `pygetwindow` (Windows), `AppKit` (macOS), `python-xlib` (Linux)

### 3. Privacy & Security Layer

**Responsibilities:**
- Enforce app whitelist/blacklist
- Mask sensitive regions
- Provide user controls
- Audit logging

**Implementation:**
```python
class PrivacyLayer:
    def __init__(self, config: PrivacyConfig):
        self.whitelist = config.whitelist  # Allowed apps
        self.blacklist = config.blacklist  # Blocked apps
        self.masked_regions = config.masked_regions
        self.is_paused = False
        
    def should_capture(self, window_info: WindowInfo) -> bool:
        """Check if window can be captured"""
        if self.is_paused:
            return False
        if window_info.process_name in self.blacklist:
            return False
        if self.whitelist and window_info.process_name not in self.whitelist:
            return False
        return True
        
    def apply_masking(self, image: Image, regions: List[Region]) -> Image:
        """Mask sensitive regions in captured image"""
```

**Privacy Controls:**
- **Visual Indicator**: Tray icon shows when AI can see screen
- **Quick Pause**: Hotkey to pause/resume
- **Granular Control**: Per-app, per-window, per-region
- **Local Only**: No data leaves the machine
- **Audit Log**: Optional logging of what was captured

### 4. Cache & History System

**Responsibilities:**
- Store recent screen states
- Implement efficient deduplication
- Provide temporal queries
- Compress historical data

**Implementation:**
```python
class ScreenCache:
    def __init__(self, max_history: int = 100):
        self.history = deque(maxlen=max_history)
        self.semantic_cache = {}  # For deduplication
        
    def add(self, capture: ScreenCapture):
        """Add capture to history with deduplication"""
        hash = self._perceptual_hash(capture.image)
        if hash not in self.semantic_cache:
            self.semantic_cache[hash] = capture
            self.history.append(capture)
            
    def get_changes_since(self, timestamp: float) -> List[ScreenCapture]:
        """Get all screen states since timestamp"""
        
    def get_last_n(self, n: int) -> List[ScreenCapture]:
        """Get last N screen captures"""
```

**Optimization Strategies:**
- **Perceptual Hashing**: Only store genuinely different screens
- **Delta Compression**: Store differences between frames
- **Lazy Loading**: Compress old captures to disk
- **TTL**: Expire old captures automatically

## 🔌 MCP Resources

### Resource URIs

```
screen://current
  - Description: Current full screen capture
  - Returns: Base64-encoded PNG of all monitors
  
screen://monitors
  - Description: List of available monitors
  - Returns: JSON array of monitor info
  
screen://monitor/{id}
  - Description: Specific monitor capture
  - Parameters: id (monitor index)
  - Returns: Base64-encoded PNG
  
screen://window/active
  - Description: Active window only
  - Returns: Base64-encoded PNG + window metadata
  
screen://window/{id}
  - Description: Specific window by ID
  - Parameters: id (window handle/ID)
  - Returns: Base64-encoded PNG
  
screen://region/{x}/{y}/{w}/{h}
  - Description: Specific screen region
  - Parameters: x, y, w, h (coordinates)
  - Returns: Base64-encoded PNG
  
screen://history/last/{n}
  - Description: Last N screen captures
  - Parameters: n (number of captures)
  - Returns: Array of captures with timestamps
  
screen://changes/since/{timestamp}
  - Description: Changes since timestamp
  - Parameters: timestamp (Unix timestamp)
  - Returns: Array of changed screens
```

### Resource Response Format

```json
{
  "uri": "screen://current",
  "mimeType": "image/png",
  "blob": "iVBORw0KGgoAAAANSUhEUg...",
  "metadata": {
    "timestamp": 1698765432.123,
    "dimensions": {
      "width": 1920,
      "height": 1080
    },
    "monitors": [
      {
        "id": 0,
        "name": "Primary Monitor",
        "bounds": {"x": 0, "y": 0, "width": 1920, "height": 1080},
        "isPrimary": true
      }
    ],
    "activeWindow": {
      "title": "Cursor - working_bot.py",
      "processName": "Cursor",
      "bounds": {"x": 100, "y": 100, "width": 1600, "height": 900}
    }
  }
}
```

## 🛠️ MCP Tools

Tools allow AI to take actions, not just query resources.

### Tool: capture_screen

```json
{
  "name": "capture_screen",
  "description": "Capture screen on-demand",
  "inputSchema": {
    "type": "object",
    "properties": {
      "target": {
        "type": "string",
        "enum": ["current", "active_window", "monitor", "region"],
        "description": "What to capture"
      },
      "monitor_id": {
        "type": "integer",
        "description": "Monitor ID (if target=monitor)"
      },
      "region": {
        "type": "object",
        "properties": {
          "x": {"type": "integer"},
          "y": {"type": "integer"},
          "width": {"type": "integer"},
          "height": {"type": "integer"}
        },
        "description": "Region coordinates (if target=region)"
      }
    },
    "required": ["target"]
  }
}
```

### Tool: analyze_ui

```json
{
  "name": "analyze_ui",
  "description": "Analyze UI/UX of current screen",
  "inputSchema": {
    "type": "object",
    "properties": {
      "aspects": {
        "type": "array",
        "items": {
          "type": "string",
          "enum": [
            "accessibility",
            "design_consistency",
            "visual_hierarchy",
            "responsive_design",
            "color_contrast",
            "spacing",
            "typography"
          ]
        },
        "description": "Which aspects to analyze"
      },
      "target": {
        "type": "string",
        "enum": ["current", "active_window"],
        "default": "active_window"
      }
    }
  }
}
```

### Tool: set_privacy_controls

```json
{
  "name": "set_privacy_controls",
  "description": "Configure privacy settings",
  "inputSchema": {
    "type": "object",
    "properties": {
      "action": {
        "type": "string",
        "enum": ["pause", "resume", "whitelist_add", "blacklist_add"]
      },
      "app_name": {
        "type": "string",
        "description": "App name (for whitelist/blacklist)"
      }
    },
    "required": ["action"]
  }
}
```

## 📝 MCP Prompts

Pre-built prompts that users can invoke.

### Prompt: Review UI

```json
{
  "name": "review_ui",
  "description": "Review current UI for issues",
  "arguments": [
    {
      "name": "focus",
      "description": "What to focus on",
      "required": false
    }
  ],
  "template": "Please review the current screen for UI/UX issues. Focus on: {{focus}}. Provide specific, actionable feedback with coordinates/locations."
}
```

### Prompt: Accessibility Audit

```json
{
  "name": "accessibility_audit",
  "description": "Audit UI for accessibility issues",
  "template": "Perform an accessibility audit of the current screen. Check for: color contrast (WCAG AA), keyboard navigation, screen reader compatibility, focus indicators, and alternative text. Provide a detailed report with severity levels."
}
```

### Prompt: Find Visual Bugs

```json
{
  "name": "find_visual_bugs",
  "description": "Detect visual bugs on screen",
  "template": "Analyze the current screen for visual bugs such as: overlapping elements, cut-off text, misaligned components, broken layouts, inconsistent spacing, missing images, and rendering issues. Report each bug with coordinates and severity."
}
```

## 🚀 Performance Optimizations

### 1. Smart Capture Strategy

**Challenge**: Constantly capturing screen is expensive.

**Solution**: Event-driven capture
```python
class SmartCaptureStrategy:
    def __init__(self):
        self.last_capture_time = 0
        self.min_interval = 0.5  # Max 2 captures per second
        self.last_hash = None
        
    def should_capture(self) -> bool:
        # Only capture if:
        # 1. Enough time has passed
        # 2. Screen has actually changed
        # 3. AI is actively querying
        if time.time() - self.last_capture_time < self.min_interval:
            return False
        if not self.has_screen_changed():
            return False
        return True
```

### 2. GPU-Accelerated Capture (Windows)

**DXGI Desktop Duplication API** (Windows 8+):
- Uses GPU to capture screen (no CPU overhead)
- Near-zero performance impact
- Supports 60+ FPS capture rates

```python
class DXGICapture:
    def __init__(self):
        self.device = self._create_d3d_device()
        self.duplicator = self._create_desktop_duplication()
        
    def capture_frame(self) -> np.ndarray:
        # GPU-accelerated capture
        frame = self.duplicator.AcquireNextFrame()
        # Returns frame in ~1-2ms
```

### 3. Differential Compression

**Challenge**: Storing many screen captures uses lots of memory.

**Solution**: Store deltas
```python
class DeltaCompressor:
    def compress(self, current: Image, previous: Image) -> bytes:
        # Only store what changed
        diff = cv2.absdiff(current, previous)
        # Compress using zlib or lz4
        return lz4.compress(diff.tobytes())
        
    def decompress(self, delta: bytes, previous: Image) -> Image:
        # Reconstruct current from previous + delta
        diff = np.frombuffer(lz4.decompress(delta), dtype=np.uint8)
        return cv2.add(previous, diff.reshape(previous.shape))
```

### 4. Perceptual Hashing

**Challenge**: Detect when screen is meaningfully different.

**Solution**: Use perceptual hashing (pHash)
```python
import imagehash

class ScreenDeduplicator:
    def __init__(self, threshold: int = 5):
        self.threshold = threshold
        self.last_hash = None
        
    def is_different(self, image: Image) -> bool:
        current_hash = imagehash.phash(image)
        if self.last_hash is None:
            self.last_hash = current_hash
            return True
        diff = current_hash - self.last_hash
        if diff > self.threshold:
            self.last_hash = current_hash
            return True
        return False
```

## 🔒 Security Considerations

### 1. Local-Only Processing
- **No cloud uploads**: All processing happens on device
- **No telemetry**: Zero data sent to external servers
- **Explicit consent**: User must enable per-app

### 2. Credential Protection
- **Auto-detect password fields**: Mask automatically
- **Sensitive apps**: Default blacklist (password managers, banking, etc.)
- **OCR scanning**: Detect credit cards, SSNs, API keys

```python
class CredentialDetector:
    def scan(self, image: Image) -> List[SensitiveRegion]:
        # Run OCR
        text = pytesseract.image_to_string(image)
        
        # Detect patterns
        credit_cards = re.findall(r'\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}', text)
        ssns = re.findall(r'\d{3}-\d{2}-\d{4}', text)
        api_keys = re.findall(r'[A-Za-z0-9]{32,}', text)
        
        # Return regions to mask
        return self._locate_sensitive_text(image, text, patterns)
```

### 3. Sandboxing
- **Minimal permissions**: Only screen capture + file write (for cache)
- **No network access**: Can run in airplane mode
- **Process isolation**: Runs as separate process from IDE

### 4. Audit Trail
```python
class AuditLogger:
    def log_capture(self, capture_info: dict):
        # Optional audit log (disabled by default)
        log_entry = {
            "timestamp": time.time(),
            "resource": capture_info["uri"],
            "window": capture_info["activeWindow"]["title"],
            "requester": "Cursor IDE",
            "user_approved": True
        }
        self.append_to_log(log_entry)
```

## 📚 Technology Stack

### Core Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.10"

# MCP SDK
mcp = "^1.0.0"

# Screen capture
mss = "^9.0.1"              # Fast cross-platform screenshots
pillow = "^10.0.0"          # Image processing
opencv-python = "^4.8.0"    # Computer vision

# Platform-specific (optional)
pywin32 = {version = "^306", platform = "win32"}    # Windows APIs
pygetwindow = "^0.0.9"      # Window management
pyautogui = "^0.9.54"       # Fallback capture

# Performance
numpy = "^1.24.0"
lz4 = "^4.3.2"              # Fast compression

# Image analysis
imagehash = "^4.3.1"        # Perceptual hashing
pytesseract = "^0.3.10"     # OCR (for credential detection)

# Utilities
pydantic = "^2.0.0"         # Config validation
python-dotenv = "^1.0.0"    # Environment config
```

### Development Dependencies

```toml
[tool.poetry.dev-dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
black = "^23.0.0"
ruff = "^0.1.0"
mypy = "^1.5.0"
```

## 📁 Project Structure

```
mcp-screen-server/
├── src/
│   ├── __init__.py
│   ├── server.py              # Main MCP server
│   ├── capture/
│   │   ├── __init__.py
│   │   ├── engine.py          # Screen capture engine
│   │   ├── windows.py         # Windows-specific (DXGI)
│   │   ├── macos.py           # macOS-specific
│   │   └── linux.py           # Linux-specific
│   ├── privacy/
│   │   ├── __init__.py
│   │   ├── layer.py           # Privacy controls
│   │   └── detector.py        # Credential detection
│   ├── cache/
│   │   ├── __init__.py
│   │   ├── history.py         # Screen history
│   │   └── compression.py     # Delta compression
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py         # Pydantic models
│   └── utils/
│       ├── __init__.py
│       └── image.py           # Image utilities
├── tests/
│   ├── test_capture.py
│   ├── test_privacy.py
│   └── test_server.py
├── config/
│   ├── default.yaml           # Default config
│   └── example.yaml           # Example user config
├── pyproject.toml
├── README.md
└── LICENSE
```

## 🔧 Configuration

### User Config (YAML)

```yaml
# ~/.config/mcp-screen-server/config.yaml

server:
  name: "screen-access"
  version: "0.1.0"

capture:
  # Capture settings
  method: "auto"  # auto, mss, dxgi, native
  quality: 85     # JPEG quality (1-100)
  max_fps: 2      # Maximum captures per second
  
  # Change detection
  enable_change_detection: true
  change_threshold: 5  # Perceptual hash difference

privacy:
  # Default: allow nothing
  mode: "whitelist"  # whitelist or blacklist
  
  whitelist:
    - "Cursor"
    - "Code"
    - "Chrome"
    - "Firefox"
  
  blacklist:
    - "1Password"
    - "Bitwarden"
    - "KeePass"
    - "Banking*"  # Wildcard support
  
  # Auto-detect and mask
  mask_credentials: true
  mask_password_fields: true
  
  # Visual indicator
  show_tray_icon: true
  
  # Hotkeys
  pause_hotkey: "Ctrl+Alt+P"

cache:
  # History settings
  max_history: 100
  max_history_age_seconds: 3600  # 1 hour
  
  # Storage
  cache_dir: "~/.cache/mcp-screen-server"
  enable_compression: true
  compression_method: "lz4"  # lz4 or zlib

performance:
  # GPU acceleration (Windows only)
  use_dxgi: true
  
  # Threading
  async_capture: true
  worker_threads: 2

logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  file: "~/.local/share/mcp-screen-server/logs/server.log"
  
  # Audit trail (optional, disabled by default)
  enable_audit: false
  audit_file: "~/.local/share/mcp-screen-server/audit.log"
```

## 🔌 Integration with Cursor

### MCP Server Configuration

Add to Cursor's MCP settings:

```json
// ~/.cursor/mcp.json (or similar)
{
  "mcpServers": {
    "screen-access": {
      "command": "python",
      "args": ["-m", "mcp_screen_server"],
      "env": {}
    }
  }
}
```

### Usage in Cursor

Once configured, AI can automatically access screen:

```
User: "Review this UI"

AI: *internally queries screen://window/active*
    Based on what I see on your screen, here are some UI issues:
    1. The button at (342, 156) has insufficient contrast...
    2. Text is cut off in the sidebar at (50, 200)...
```

## 🧪 Testing Strategy

### Unit Tests

```python
# tests/test_capture.py
def test_screen_capture():
    engine = ScreenCaptureEngine()
    capture = engine.capture_current()
    assert capture.image is not None
    assert capture.metadata["dimensions"]["width"] > 0

def test_change_detection():
    detector = ChangeDetector()
    assert detector.has_changed(image1, image1) == False
    assert detector.has_changed(image1, image2) == True
```

### Integration Tests

```python
# tests/test_server.py
@pytest.mark.asyncio
async def test_mcp_resource():
    server = ScreenMCPServer()
    resources = await server.list_resources()
    assert "screen://current" in [r.uri for r in resources]
    
    capture = await server.read_resource("screen://current")
    assert capture.mimeType == "image/png"
    assert len(capture.blob) > 0
```

### Manual Testing Checklist

- [ ] Capture full screen
- [ ] Capture active window only
- [ ] Capture specific monitor (multi-monitor)
- [ ] Capture region
- [ ] Privacy controls work (whitelist/blacklist)
- [ ] Change detection works
- [ ] History retrieval works
- [ ] Performance acceptable (<50ms per capture)
- [ ] Works in Cursor IDE
- [ ] Tray icon shows/hides correctly

## 📊 Performance Targets

| Metric | Target | Stretch Goal |
|--------|--------|--------------|
| Capture latency | <50ms | <10ms |
| Memory usage | <200MB | <100MB |
| CPU usage (idle) | <1% | <0.5% |
| CPU usage (active) | <10% | <5% |
| Storage (100 captures) | <50MB | <20MB |
| Startup time | <2s | <1s |

## 🚢 Deployment

### Installation (End User)

```bash
# Via pip
pip install mcp-screen-server

# Via pipx (recommended)
pipx install mcp-screen-server

# Configure
mcp-screen-server init  # Creates config file

# Add to Cursor
mcp-screen-server integrate cursor
```

### Development Setup

```bash
# Clone repo
git clone https://github.com/yourusername/mcp-screen-server
cd mcp-screen-server

# Install with Poetry
poetry install

# Run tests
poetry run pytest

# Run server (for testing)
poetry run python -m mcp_screen_server
```

## 🎯 Future Enhancements

### Phase 2 Features
- **OCR integration**: Extract text from screen automatically
- **UI element detection**: Identify buttons, inputs, etc.
- **Screen recording**: Video capture for tutorials
- **Multi-user support**: Team screen sharing

### Phase 3 Features
- **Browser integration**: Inspect element directly
- **Mobile support**: Capture mobile device screens
- **Cloud sync**: Optional encrypted cloud backup
- **AI fine-tuning**: Custom models for design systems

---

**This spec provides everything needed to build the MVP and scale to a full product.**

Next: See `BUILD_PLAN.md` for step-by-step implementation guide.

