# ScreenCapture MCP Server

> Give your AI assistant eyes. Capture and analyze your screen directly from Cursor, Claude Code, or any MCP-compatible editor.

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://python.org)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCI+PHJlY3Qgd2lkdGg9IjI0IiBoZWlnaHQ9IjI0IiByeD0iNCIgZmlsbD0iIzRjYWY1MCIvPjwvc3ZnPg==)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

---

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that lets AI assistants **autonomously capture and analyze your screen** — no manual screenshots, no copy-paste, no uploads. Just ask.

```
You:  "Capture my screen and review the UI"
AI:   *captures screen, analyzes colors, layout, spacing, and gives actionable feedback*
```

## Why?

Every time you want AI help with a design, you have to: screenshot, save, upload, wait. **This eliminates all of that.** Your AI assistant can now see exactly what you see, instantly.

---

## Features

**10 tools** your AI assistant can use autonomously:

| Tool | What It Does |
|------|-------------|
| `capture_screen` | Full screen or specific monitor capture |
| `capture_region` | Capture any rectangular area (x, y, w, h) |
| `capture_active_window` | Capture just the focused window |
| `analyze_design` | Full design DNA extraction (colors, layout, typography, spacing) |
| `extract_color` | Get exact color at any screen coordinate (hex, RGB, HSV) |
| `analyze_color_palette` | Find dominant colors in any region |
| `check_contrast` | WCAG accessibility contrast ratio checker |
| `start_continuous_capture` | Time-lapse capture with optional OCR text extraction |
| `get_monitor_info` | List all monitors with resolutions |
| `cleanup_logs` | Maintenance — remove old log files |

**4 built-in prompts** for common workflows:
- `review_ui` — Comprehensive UI/UX review
- `check_accessibility` — WCAG compliance audit
- `quick_design_check` — Quick design issues scan
- `color_analysis` — Color usage and contrast analysis

---

## Quick Start

### Prerequisites

- Python 3.10+
- An MCP-compatible editor ([Cursor](https://cursor.com), [Claude Code](https://claude.com/claude-code), etc.)

### Install

```bash
git clone https://github.com/xDarkzx/ScreenCapture-MCP.git
cd ScreenCapture-MCP
pip install -r requirements.txt
```

### Configure Your Editor

<details>
<summary><b>Cursor</b></summary>

Add to your Cursor MCP settings:

```json
{
  "mcpServers": {
    "screen-access": {
      "command": "python",
      "args": ["-m", "src"],
      "cwd": "/path/to/ScreenCapture-MCP"
    }
  }
}
```

Restart Cursor. Look for **"screen-access"** with a green dot in the MCP panel.
</details>

<details>
<summary><b>Claude Code</b></summary>

```bash
claude mcp add screen-access -- python -m src --cwd /path/to/ScreenCapture-MCP
```
</details>

<details>
<summary><b>Other MCP Editors</b></summary>

Point your MCP config to:
- **Command:** `python`
- **Args:** `["-m", "src"]`
- **Working directory:** the cloned repo folder
</details>

### Test It

Ask your AI: **"Capture my screen and tell me what you see"**

---

## Usage Examples

### Design Review
```
"Capture my screen and review the spacing and alignment"
```

### Accessibility Audit
```
"Check if the text on my landing page meets WCAG contrast standards"
```

### Color Extraction
```
"What are the exact colors used in this design?"
```

### Code from Screenshot
```
"Capture this landing page and recreate it in HTML/CSS"
```

### Continuous Capture (for scrolling content)
```
"Start continuous capture for 30 seconds while I scroll through this documentation"
```

### Multi-Monitor
```
"Capture my second monitor and analyze the layout"
```

---

## Architecture

```
┌─────────────────┐    MCP/stdio     ┌──────────────────────┐
│   AI Editor     │ ◄──────────────► │  ScreenCapture MCP   │
│  (Cursor, etc.) │                  │  Server (Python)     │
└─────────────────┘                  └──────────┬───────────┘
                                                │
                                     ┌──────────▼───────────┐
                                     │  Capture Engine      │
                                     │  - mss (screen grab) │
                                     │  - Pillow (analysis) │
                                     │  - OCR (optional)    │
                                     └──────────────────────┘
                                                │
                                         In-memory only
                                        (no disk writes)
```

**Privacy by design:**
- 100% local — nothing leaves your machine
- In-memory only — no screenshots saved to disk
- No telemetry — zero data sent anywhere
- Open source — audit the code yourself

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp` | Model Context Protocol SDK |
| `mss` | Fast cross-platform screen capture |
| `Pillow` | Image processing and analysis |
| `pywin32` | Windows window detection (Windows only) |
| `easyocr` | Optional — text extraction from screenshots |
| `numpy` | Required by easyocr |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| MCP showing red/yellow | Check the path in your config, make sure Python is installed |
| MCP not appearing | Fully restart your editor, verify JSON config syntax |
| "No module named src" | Make sure `cwd` points to the repo root |
| OCR not working | Install easyocr: `pip install easyocr` (optional feature) |
| Active window capture fails | Windows only — falls back to full screen on other platforms |

Check `mcp_server.log` in the project folder for detailed error messages.

---

## Contributing

Contributions welcome! Open an issue or submit a PR.

## License

[MIT](LICENSE)

---

**Built for the MCP ecosystem** — works with any editor that supports the [Model Context Protocol](https://modelcontextprotocol.io).
