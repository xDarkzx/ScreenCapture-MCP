# 🚀 Quick Install Guide - Screen Access MCP for Cursor

**Get AI agents to see your screen in under 5 minutes.**

---

## ✅ Prerequisites

- **Cursor IDE** (v0.43 or later)
- **Python 3.10+** installed
- **Windows/macOS/Linux**

---

## 📦 Step 1: Download & Install

### **1. Download this project**
```bash
# If using git:
git clone https://github.com/xDarkzx/ScreenCapture-MCP.git
cd ScreenCapture-MCP

# Or download ZIP and extract
```

### **2. Install Python dependencies**
```bash
# On Windows (in PowerShell):
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# On macOS/Linux:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## ⚙️ Step 2: Configure Cursor

### **1. Find your Cursor MCP config file:**

**Windows:**
```
%APPDATA%\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json
```

**macOS:**
```
~/Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json
```

**Linux:**
```
~/.config/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json
```

### **2. Add the MCP server config:**

Open the file and add this (replace `YOUR_PATH_HERE` with actual path):

```json
{
  "mcpServers": {
    "screen-access": {
      "command": "YOUR_PATH_HERE\\venv\\Scripts\\python.exe",
      "args": ["-m", "src"],
      "cwd": "YOUR_PATH_HERE"
    }
  }
}
```

**Example (Windows):**
```json
{
  "mcpServers": {
    "screen-access": {
      "command": "D:\\Projects\\AIMCPIDEA\\venv\\Scripts\\python.exe",
      "args": ["-m", "src"],
      "cwd": "D:\\Projects\\AIMCPIDEA"
    }
  }
}
```

**Example (macOS/Linux):**
```json
{
  "mcpServers": {
    "screen-access": {
      "command": "/Users/yourname/AIMCPIDEA/venv/bin/python",
      "args": ["-m", "src"],
      "cwd": "/Users/yourname/AIMCPIDEA"
    }
  }
}
```

---

## 🔄 Step 3: Restart Cursor

1. **Close Cursor completely**
2. **Reopen Cursor**
3. Look for **"screen-access"** in the MCP panel (should show green dot ✅)

---

## ✅ Step 4: Test It!

Open Cursor and try:

```
"Capture my screen and tell me what you see"
```

or

```
"Take a screenshot of my second monitor"
```

If the AI can see and describe your screen - **you're done!** 🎉

---

## 🛠️ Troubleshooting

### **MCP showing red/yellow?**
1. Check the path in your config is correct
2. Make sure Python venv is created: `.\venv\Scripts\python.exe` should exist
3. Try running manually: `.\venv\Scripts\python.exe -m src` (should show logs)

### **MCP not appearing?**
1. Restart Cursor (fully quit and reopen)
2. Check config file syntax (valid JSON?)
3. Look for MCP settings in Cursor: `Ctrl+Shift+P` → "MCP Settings"

### **Still stuck?**
Check `mcp_server.log` in the project folder for error messages.

---

## 🎯 What You Can Do Now

### **Available Tools:**

1. **`capture_screen`** - Capture full screen or specific monitor
2. **`capture_region`** - Capture part of screen (x, y, width, height)
3. **`capture_active_window`** - Capture just the focused window
4. **`extract_color`** - Get color at specific coordinates
5. **`analyze_color_palette`** - Find dominant colors in region
6. **`check_contrast`** - WCAG accessibility contrast check
7. **`start_continuous_capture`** - Time-lapse capture (for scrolling docs)

### **Example Prompts:**

```
"Analyze the colors in this website design"
"Check if my button has good contrast for accessibility"
"Capture my second monitor and redesign that landing page"
"What fonts are being used in this design?"
```

---

## 📚 Next Steps

- See **docs/USAGE_EXAMPLES.md** for more examples
- See **docs/TECHNICAL_DETAILS.md** for how it works
- See **docs/CONTRIBUTING.md** if you want to improve it

---

## 🤝 Need Help?

- Check `mcp_server.log` for errors
- Open an issue on GitHub
- Ask in Cursor community forums

---

**Enjoy autonomous visual AI! 🚀**


