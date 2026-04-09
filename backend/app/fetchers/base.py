from abc import ABC, abstractmethod
from typing import Any

import httpx
import logging

logger = logging.getLogger(__name__)


def truncate_body(text: str, max_length: int = 500) -> str:
    """Truncate text to max_length characters."""
    if not text:
        return ""
    return text[:max_length]


class BaseFetcher(ABC):
    TIMEOUT = 10.0
    MAX_RETRIES = 2

    @abstractmethod
    async def fetch(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch raw items from source. Returns list of raw item dicts."""
        ...

    @abstractmethod
    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Normalize raw item into canonical format:
        {source, source_url, original_title, original_body, source_metadata, engagement_metric}
        """
        ...

    async def safe_fetch(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch with error handling. Returns empty list on failure."""
        try:
            raw_items = await self.fetch(client)
            return [self.normalize(item) for item in raw_items]
        except httpx.TimeoutException:
            logger.warning(f"{self.__class__.__name__}: Request timed out")
            return []
        except httpx.HTTPStatusError as e:
            logger.warning(f"{self.__class__.__name__}: HTTP {e.response.status_code}")
            return []
        except Exception as e:
            logger.warning(f"{self.__class__.__name__}: Error: {e}")
            return []
