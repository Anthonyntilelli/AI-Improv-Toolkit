"""
Ingest role module.
Use the main function to start the ingest process.
"""

import asyncio
import config as cfg

async def main(config: cfg.Config) -> None:
    print("Ingest role started with config:", config)
    # Placeholder for actual ingest logic
    await asyncio.sleep(1)
    print("Ingest role completed.")
