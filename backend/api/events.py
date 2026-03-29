import asyncio
import json

# Global queue for SSE alerts
# Initialized in api/main.py or by first importer
alert_queue = asyncio.Queue()
