"""Diagnostic script to test each source fetcher independently."""

import asyncio
import json
import sys

import httpx
import feedparser


TIMEOUT = 15.0
DIVIDER = "=" * 60


async def test_steam():
    """Test 1: Steam Store featured categories API."""
    print(DIVIDER)
    print("[TEST 1] Steam Store API")
    url = "https://store.steampowered.com/api/featuredcategories/?cc=us&l=english"
    print(f"  URL: {url}")

    try:
        async with httpx.AsyncClient(trust_env=False, timeout=TIMEOUT) as client:
            resp = await client.get(url)
            print(f"  Status code: {resp.status_code}")
            print(f"  Content-Type: {resp.headers.get('content-type', 'N/A')}")
            print(f"  Content length: {len(resp.content)} bytes")

            if resp.status_code != 200:
                print(f"  FAIL: Non-200 status code")
                print(f"  Response body (first 500 chars): {resp.text[:500]}")
                return

            data = resp.json()

            top_sellers = data.get("top_sellers")
            coming_soon = data.get("coming_soon")
            print(f"  top_sellers key present: {top_sellers is not None}")
            print(f"  coming_soon key present: {coming_soon is not None}")

            if top_sellers:
                items = top_sellers.get("items", [])
                print(f"  top_sellers item count: {len(items)}")
                if items:
                    print(f"  First top_seller: id={items[0].get('id')}, name={items[0].get('name')}")
            else:
                print(f"  top_sellers value: {top_sellers}")

            if coming_soon:
                items = coming_soon.get("items", [])
                print(f"  coming_soon item count: {len(items)}")
                if items:
                    print(f"  First coming_soon: id={items[0].get('id')}, name={items[0].get('name')}")
            else:
                print(f"  coming_soon value: {coming_soon}")

            # Print all top-level keys to help debug
            print(f"  All top-level keys in response: {list(data.keys())}")

            # Check if data looks valid for SteamFetcher
            ts_items = data.get("top_sellers", {}).get("items", [])
            cs_items = data.get("coming_soon", {}).get("items", [])
            total = len(ts_items) + len(cs_items)
            if total > 0:
                print(f"  SUCCESS: {total} items total ({len(ts_items)} top_sellers + {len(cs_items)} coming_soon)")
            else:
                print(f"  FAIL: 0 items extracted (top_sellers items={len(ts_items)}, coming_soon items={len(cs_items)})")

    except httpx.TimeoutException as e:
        print(f"  FAIL: Timeout - {e}")
    except httpx.HTTPStatusError as e:
        print(f"  FAIL: HTTP {e.response.status_code}")
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {e}")


async def test_animeanime_rss():
    """Test 2: Anime! Anime! RSS feed."""
    print(DIVIDER)
    print("[TEST 2] Anime! Anime! RSS")
    url = "https://animeanime.jp/rss/index.rdf"
    print(f"  URL: {url}")

    try:
        async with httpx.AsyncClient(trust_env=False, timeout=TIMEOUT) as client:
            resp = await client.get(url)
            print(f"  Status code: {resp.status_code}")
            print(f"  Content-Type: {resp.headers.get('content-type', 'N/A')}")
            print(f"  Content length: {len(resp.content)} bytes")

            if resp.status_code != 200:
                print(f"  FAIL: Non-200 status code")
                print(f"  Response body (first 500 chars): {resp.text[:500]}")
                return

            feed = feedparser.parse(resp.content)
            print(f"  Feed parsed entries: {len(feed.entries)}")

            if feed.bozo:
                print(f"  WARNING: feedparser bozo=True, bozo_exception: {feed.bozo_exception}")

            if feed.entries:
                print(f"  First entry title: {feed.entries[0].get('title', 'N/A')}")
                print(f"  First entry link: {feed.entries[0].get('link', 'N/A')}")
                print(f"  SUCCESS: {len(feed.entries)} entries parsed")
            else:
                print(f"  FAIL: 0 entries parsed")
                print(f"  Raw content (first 500 chars): {resp.text[:500]}")

    except httpx.TimeoutException as e:
        print(f"  FAIL: Timeout - {e}")
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {e}")


async def test_animate_rss():
    """Test 3: Animate RSS feed."""
    print(DIVIDER)
    print("[TEST 3] Animate RSS")
    url = "https://www.animate.co.jp/feed/"
    print(f"  URL: {url}")

    try:
        async with httpx.AsyncClient(trust_env=False, timeout=TIMEOUT) as client:
            resp = await client.get(url)
            print(f"  Status code: {resp.status_code}")
            print(f"  Content-Type: {resp.headers.get('content-type', 'N/A')}")
            print(f"  Content length: {len(resp.content)} bytes")

            if resp.status_code != 200:
                print(f"  FAIL: Non-200 status code")
                print(f"  Response body (first 500 chars): {resp.text[:500]}")
                return

            feed = feedparser.parse(resp.content)
            print(f"  Feed parsed entries: {len(feed.entries)}")

            if feed.bozo:
                print(f"  WARNING: feedparser bozo=True, bozo_exception: {feed.bozo_exception}")

            if feed.entries:
                print(f"  First entry title: {feed.entries[0].get('title', 'N/A')}")
                print(f"  First entry link: {feed.entries[0].get('link', 'N/A')}")
                print(f"  SUCCESS: {len(feed.entries)} entries parsed")
            else:
                print(f"  FAIL: 0 entries parsed")
                print(f"  Raw content (first 500 chars): {resp.text[:500]}")

    except httpx.TimeoutException as e:
        print(f"  FAIL: Timeout - {e}")
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {e}")


async def test_anilist():
    """Test 4: AniList GraphQL API."""
    print(DIVIDER)
    print("[TEST 4] AniList GraphQL")
    url = "https://graphql.anilist.co"
    query = """
    query {
      TrendingAnime: Page(page: 1, perPage: 25) {
        media(sort: TRENDING_DESC, type: ANIME, isAdult: false) {
          id
          title { romaji english }
          trending
          popularity
          siteUrl
        }
      }
      TrendingManga: Page(page: 1, perPage: 15) {
        media(sort: TRENDING_DESC, type: MANGA, isAdult: false) {
          id
          title { romaji english }
          trending
          popularity
          siteUrl
        }
      }
    }
    """
    print(f"  URL: {url}")

    try:
        async with httpx.AsyncClient(trust_env=False, timeout=TIMEOUT) as client:
            resp = await client.post(url, json={"query": query})
            print(f"  Status code: {resp.status_code}")
            print(f"  Content-Type: {resp.headers.get('content-type', 'N/A')}")

            if resp.status_code != 200:
                print(f"  FAIL: Non-200 status code")
                print(f"  Response body (first 500 chars): {resp.text[:500]}")
                return

            data = resp.json()
            anime_media = data.get("data", {}).get("TrendingAnime", {}).get("media", [])
            manga_media = data.get("data", {}).get("TrendingManga", {}).get("media", [])
            total = len(anime_media) + len(manga_media)
            print(f"  TrendingAnime count: {len(anime_media)}")
            print(f"  TrendingManga count: {len(manga_media)}")

            if anime_media:
                first = anime_media[0]
                title = first.get("title", {}).get("romaji") or first.get("title", {}).get("english")
                print(f"  First anime: {title} (trending={first.get('trending')})")

            if total > 0:
                print(f"  SUCCESS: {total} items ({len(anime_media)} anime + {len(manga_media)} manga)")
            else:
                print(f"  FAIL: 0 items returned")

    except httpx.TimeoutException as e:
        print(f"  FAIL: Timeout - {e}")
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {e}")


async def test_reddit():
    """Test 5: Reddit OAuth + fetch (if credentials configured)."""
    print(DIVIDER)
    print("[TEST 5] Reddit")

    # Check .env for Reddit credentials
    try:
        with open(".env") as f:
            env_content = f.read()
    except FileNotFoundError:
        env_content = ""

    client_id = ""
    client_secret = ""
    for line in env_content.splitlines():
        line = line.strip()
        if line.startswith("REDDIT_CLIENT_ID="):
            client_id = line.split("=", 1)[1].strip().strip('"').strip("'")
        elif line.startswith("REDDIT_CLIENT_SECRET="):
            client_secret = line.split("=", 1)[1].strip().strip('"').strip("'")

    if not client_id or not client_secret:
        print(f"  SKIP: REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET not set in .env")
        print(f"    client_id present: {bool(client_id)}")
        print(f"    client_secret present: {bool(client_secret)}")
        return

    token_url = "https://www.reddit.com/api/v1/access_token"
    user_agent = "acgfeed/1.0"
    print(f"  Token URL: {token_url}")
    print(f"  Client ID: {client_id[:4]}...{client_id[-4:]}" if len(client_id) > 8 else f"  Client ID: {client_id}")

    try:
        async with httpx.AsyncClient(trust_env=False, timeout=TIMEOUT) as client:
            # Step 1: Get OAuth token
            resp = await client.post(
                token_url,
                data={"grant_type": "client_credentials"},
                auth=(client_id, client_secret),
                headers={"User-Agent": user_agent},
            )
            print(f"  Token request status: {resp.status_code}")

            if resp.status_code != 200:
                print(f"  FAIL: Could not obtain OAuth token")
                print(f"  Response: {resp.text[:300]}")
                return

            token = resp.json().get("access_token", "")
            if not token:
                print(f"  FAIL: No access_token in response")
                return

            print(f"  Token obtained: {token[:8]}...")

            # Step 2: Fetch hot posts from r/anime
            headers = {
                "Authorization": f"Bearer {token}",
                "User-Agent": user_agent,
            }
            resp = await client.get(
                "https://oauth.reddit.com/r/anime/hot",
                headers=headers,
                params={"limit": 5},
            )
            print(f"  r/anime/hot status: {resp.status_code}")

            if resp.status_code != 200:
                print(f"  FAIL: Non-200 fetching subreddit")
                print(f"  Response: {resp.text[:300]}")
                return

            data = resp.json()
            children = data.get("data", {}).get("children", [])
            print(f"  Posts returned: {len(children)}")

            if children:
                first = children[0].get("data", {})
                print(f"  First post: {first.get('title', 'N/A')[:60]}")
                print(f"  SUCCESS: Reddit OAuth + fetch works ({len(children)} posts from r/anime)")
            else:
                print(f"  FAIL: 0 posts returned")

    except httpx.TimeoutException as e:
        print(f"  FAIL: Timeout - {e}")
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {e}")


async def test_fetcher_classes():
    """Test 6: Run actual fetcher classes (same as orchestrator)."""
    print(DIVIDER)
    print("[TEST 6] Actual Fetcher Classes (via safe_fetch)")
    print()

    from app.fetchers.steam import SteamFetcher
    from app.fetchers.rss import RSSFetcher
    from app.fetchers.anilist import AniListFetcher
    from app.fetchers.reddit import RedditFetcher

    fetchers = {
        "SteamFetcher": SteamFetcher(),
        "RSSFetcher": RSSFetcher(),
        "AniListFetcher": AniListFetcher(),
    }

    # Reddit only if creds exist
    try:
        with open(".env") as f:
            env_content = f.read()
        cid = ""
        csec = ""
        for line in env_content.splitlines():
            line = line.strip()
            if line.startswith("REDDIT_CLIENT_ID="):
                cid = line.split("=", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("REDDIT_CLIENT_SECRET="):
                csec = line.split("=", 1)[1].strip().strip('"').strip("'")
        if cid and csec:
            fetchers["RedditFetcher"] = RedditFetcher(cid, csec)
    except Exception:
        pass

    async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
        for name, fetcher in fetchers.items():
            try:
                results = await fetcher.safe_fetch(client)
                if results:
                    print(f"  {name}: SUCCESS ({len(results)} items)")
                    # Show first item summary
                    first = results[0]
                    title = first.get("original_title", "")[:60]
                    print(f"    First item: {title}")
                else:
                    print(f"  {name}: FAIL (0 items returned)")
            except Exception as e:
                print(f"  {name}: EXCEPTION - {type(e).__name__}: {e}")


async def main():
    print("=" * 60)
    print("ACG Feed Source Diagnostics")
    print("=" * 60)
    print()

    await test_steam()
    print()
    await test_animeanime_rss()
    print()
    await test_animate_rss()
    print()
    await test_anilist()
    print()
    await test_reddit()
    print()
    await test_fetcher_classes()

    print()
    print(DIVIDER)
    print("Diagnostics complete.")


if __name__ == "__main__":
    asyncio.run(main())
