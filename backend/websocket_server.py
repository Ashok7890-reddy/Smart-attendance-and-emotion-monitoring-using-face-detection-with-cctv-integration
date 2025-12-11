"""
WebSocket server entry point for Smart Attendance System.
This module starts the WebSocket notification server for real-time updates.
"""

import asyncio
import logging
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import only the websocket notification server (avoid importing services/__init__.py)
from backend.services.websocket_notification_server import start_notification_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for WebSocket server."""
    try:
        logger.info("Starting WebSocket Notification Server...")
        
        # Get host and port from environment or use defaults
        import os
        host = os.getenv("WEBSOCKET_HOST", "0.0.0.0")
        port = int(os.getenv("WEBSOCKET_PORT", "8080"))
        
        logger.info(f"WebSocket server will listen on {host}:{port}")
        
        # Run the server
        asyncio.run(start_notification_server(host=host, port=port))
        
    except KeyboardInterrupt:
        logger.info("WebSocket server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start WebSocket server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
