"""Entry point for running the MCP server as a module"""
import asyncio
from src.server import main

if __name__ == "__main__":
    asyncio.run(main())

