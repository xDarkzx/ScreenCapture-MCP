#!/usr/bin/env python
"""Direct entry point for MCP server - for Cursor compatibility"""
import sys
import os

# Add project root to path so imports work
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Now run the server
if __name__ == "__main__":
    import asyncio
    from src.server import main
    asyncio.run(main())

