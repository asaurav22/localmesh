import asyncio
import logging
import os
import httpx
from data_plane.routing_table import update_routes

logger = logging.getLogger(__name__)

CONTROL_PLANE_URL = os.getenv("CONTROL_PLANE_URL", "http://localhost:7000")
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL_SECONDS", "5"))


async def sync_loop() -> None:
    """
    Background task - polls Control Plane every SYNC_INTERVAL seconds
    and refreshes the local routing table with live registry data.
    This makes the sidecar eventually consistent with the Control plane.
    """
    logger.info(f"[SYNC] Starting sync loop - interval  {SYNC_INTERVAL}s")
    async with httpx.AsyncClient() as client:
        while True:
            await asyncio.sleep(SYNC_INTERVAL)
            try:
                response = await client.get(
                    f"{CONTROL_PLANE_URL}/registry/services",
                    timeout=3.0
                )
                response.raise_for_status()

                # control plane returns list of ServiceEntryWithExpiry
                # convert to {service_name: {host, port}} for routing table
                services = response.json()
                new_routes = {
                    s["service_name"]: {
                        "host": s["host"],
                        "port": s["port"]
                    }
                    for s in services
                }

                await update_routes(new_routes)
                logger.info(f"[SYNC] Routing table refreshed - {len(new_routes)} service(s) active")
            except httpx.TimeoutException:
                logger.warning("[SYNC] Control plane timed out - keeping existing routing table")
            except httpx.HTTPStatusError as e:
                logger.error(f"[SYNC] Control plane returned error: {e.response.status_code}")
            except Exception as e:
                logger.error(f"[SYNC] Unexpected error: {e}")
