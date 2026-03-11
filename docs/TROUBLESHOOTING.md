# MCP Server Troubleshooting Guide

## Issue: Red Dot in Cursor (Server Not Connecting)

### What Was Fixed
The server was logging to stdout, which corrupted MCP's JSON-RPC communication. This has been fixed by redirecting logs to stderr.

### How to Restart MCP Server in Cursor

#### Method 1: Reload from Settings
1. Open Cursor Settings: `Ctrl + ,` (Windows/Linux) or `Cmd + ,` (Mac)
2. Search for "MCP" in the search bar
3. Navigate to: **Features → Model Context Protocol**
4. Find your `screen-access` server in the list
5. Click the **reload/restart icon** next to it

#### Method 2: Restart Cursor
1. Close Cursor completely (make sure it's not running in the background)
2. Reopen Cursor
3. Wait for MCP servers to reconnect (look for the status indicator)

#### Method 3: Use Command Palette
1. Press `Ctrl + Shift + P` (Windows/Linux) or `Cmd + Shift + P` (Mac)
2. Type: "MCP: Reload" or "Developer: Reload"
3. Select the appropriate command

---

## Expected Results After Fix

Once the server connects successfully (green dot ✅), you should see:

### Tools (2)
- `capture_screen` - Capture the user's screen right now
- `get_monitor_info` - Get information about all available monitors

### Resources (3+)
- `screen://current` - Current Screen
- `screen://all` - All Monitors
- `screen://monitor/1` - Monitor 1 (3440x1440)
- `screen://monitor/2` - Monitor 2 (1920x1080)

### Prompts (2)
- `review_ui` - Review the current screen for UI/UX issues
- `check_accessibility` - Check the current screen for accessibility issues

---

## Still Having Issues?

### Check the Cursor Logs
1. Open Command Palette: `Ctrl + Shift + P`
2. Type: "Developer: Toggle Developer Tools"
3. Go to the Console tab
4. Look for MCP-related errors

### Verify Server Configuration
Your `cursor-mcp-config.json` should look like this:
```json
{
  "mcpServers": {
    "screen-access": {
      "command": "D:\\DansProject\\AIMCPIDEA\\venv\\Scripts\\python.exe",
      "args": ["-m", "src"],
      "cwd": "D:\\DansProject\\AIMCPIDEA"
    }
  }
}
```

### Test Server Manually
Run the server manually to see if there are any errors:
```bash
cd D:\DansProject\AIMCPIDEA
.\venv\Scripts\python.exe -m src
```

You should see:
```
INFO:src.server:Screen MCP Server initialized
INFO:src.server:Detected monitors: [...]
INFO:src.server:Starting MCP Screen Server...
```

If you see errors instead, that's your problem!

### Common Issues

#### ModuleNotFoundError: No module named 'mcp'
**Solution**: Install dependencies in venv
```bash
cd D:\DansProject\AIMCPIDEA
.\venv\Scripts\activate
pip install -r requirements.txt
```

#### ModuleNotFoundError: No module named 'src'
**Solution**: Make sure you're running from the project root with correct paths in config

#### Server starts but red dot persists
**Solution**: 
1. Check Cursor version (needs to support MCP)
2. Check if the config file is in the right location
3. Try completely restarting Cursor

---

## Testing the Server

Once connected, try asking Claude:
- "Can you capture my screen?"
- "What monitors do I have available?"
- "Show me what's on my screen right now"
- "Review my UI for accessibility issues"

The AI should be able to:
1. See and list your available monitors
2. Capture screenshots
3. Analyze what's on your screen
4. Provide feedback on UI/UX

---

## Technical Details

### Why Logging to stdout Broke MCP
- MCP uses stdin/stdout for JSON-RPC communication
- Any output to stdout (print, logs) corrupts the message stream
- Solution: All logs must go to stderr instead

### Changes Made
- `src/server.py`: Added `stream=sys.stderr` to logging config
- `src/capture/engine.py`: Commented out print statement in `__init__`

### How MCP Communication Works
```
Cursor (Client) ←→ [stdin/stdout JSON-RPC] ←→ Your Server
                   ↓
                 stderr (logs, safe!)
```

If anything writes to stdout except JSON-RPC messages, the protocol breaks.



