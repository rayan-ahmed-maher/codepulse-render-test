"""
In-Memory State Store
=====================
AsyncIO-safe dictionary for tracking deployment statuses.
Replacement for a real database during development.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime


class StateStore:
    """Thread-safe in-memory store for deployment tracking."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._deployments: Dict[str, Dict[str, Any]] = {}

    async def create(self, tracking_id: str, data: Dict[str, Any]) -> None:
        async with self._lock:
            self._deployments[tracking_id] = {
                **data,
                "tracking_id": tracking_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

    async def update(self, tracking_id: str, updates: Dict[str, Any]) -> None:
        async with self._lock:
            if tracking_id in self._deployments:
                self._deployments[tracking_id].update(updates)
                self._deployments[tracking_id]["updated_at"] = datetime.utcnow().isoformat()

    async def get(self, tracking_id: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            return self._deployments.get(tracking_id)

    async def list_all(self) -> list:
        async with self._lock:
            return list(self._deployments.values())


# Singleton instance
deployment_store = StateStore()
