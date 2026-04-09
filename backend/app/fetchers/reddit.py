"""Reddit source fetcher using OAuth2 client_credentials flow."""

from typing import Any

import httpx
import logging

from app.fetchers.base import BaseFetcher, truncate_body

logger = logging.getLogger(__name__)

# Subreddits to fetch hot posts from
SUPPORTED_SUBREDDITS = ["anime", "manga", "Games"]


class RedditFetcher(BaseFetcher):
    """Fetches trending posts from anime/manga/gaming subreddits."""

    TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
    BASE_URL = "https://oauth.reddit.com"

    def __init__(self, client_id: str, client_secret: str, user_agent: str = "acgfeed/1.0"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self._token: str | None = None

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        """Obtain or return cached OAuth2 access token."""
        if self._token:
            return self._token

        response = await client.post(
            self.TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(self.client_id, self.client_secret),
            headers={"User-Agent": self.user_agent},
            timeout=self.TIMEOUT,
        )
        response.raise_for_status()
        self._token = response.json()["access_token"]
        return self._token

    async def _invalidate_token(self) -> None:
        """Clear cached token (e.g. after a 401)."""
        self._token = None

    async def fetch(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch hot posts from configured subreddits."""
        token = await self._get_token(client)
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": self.user_agent,
        }

        all_items: list[dict[str, Any]] = []

        for subreddit in SUPPORTED_SUBREDDITS:
            url = f"{self.BASE_URL}/r/{subreddit}/hot"
            params = {"limit": 25}

            response = await client.get(
                url, headers=headers, params=params, timeout=self.TIMEOUT,
            )

            if response.status_code == 401:
                # Token expired, refresh once
                await self._invalidate_token()
                token = await self._get_token(client)
                headers["Authorization"] = f"Bearer {token}"
                response = await client.get(
                    url, headers=headers, params=params, timeout=self.TIMEOUT,
                )

            response.raise_for_status()
            data = response.json()
            children = data.get("data", {}).get("children", [])
            for child in children:
                post = child.get("data", {})
                post["_subreddit"] = subreddit
                all_items.append(post)

        return all_items

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Normalize a Reddit post into canonical format."""
        permalink = raw.get("permalink", "")
        return {
            "source": "reddit",
            "source_url": f"https://www.reddit.com{permalink}",
            "original_title": raw.get("title", ""),
            "original_body": truncate_body(raw.get("selftext", "")),
            "source_metadata": {
                "subreddit": raw.get("_subreddit", raw.get("subreddit", "")),
                "ups": raw.get("ups", 0),
                "num_comments": raw.get("num_comments", 0),
                "permalink": permalink,
                "author": raw.get("author", ""),
            },
            "engagement_metric": raw.get("ups", 0),
        }
