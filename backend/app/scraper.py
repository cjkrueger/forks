import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

import httpx
from recipe_scrapers import scrape_html

from app.url_validator import validate_url, SSRFError

logger = logging.getLogger(__name__)

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _check_redirect(response: httpx.Response) -> None:
    """httpx event hook: validate each redirect destination before following it.

    This prevents SSRF via open redirects — e.g. a public URL that redirects
    to an internal address (169.254.x.x, 10.x.x.x, etc.).

    The hook is called *before* the redirect is followed, so raising here
    causes httpx to abort the request chain.
    """
    if response.is_redirect:
        location = response.headers.get("location", "")
        if location:
            # Resolve relative redirects against the current URL
            next_url = str(response.url.copy_with()).rstrip("/")
            try:
                resolved = httpx.URL(location)
                if not resolved.is_absolute_url:
                    resolved = response.url.copy_with(path=location)
                validate_url(str(resolved))
            except SSRFError as exc:
                raise SSRFError(
                    f"Redirect to '{location}' was blocked: {exc}"
                ) from exc


def scrape_recipe(url: str) -> Dict[str, Any]:
    """Scrape a recipe from a URL and return structured data."""
    result: Dict[str, Any] = {
        "title": None,
        "author": None,
        "ingredients": [],
        "instructions": [],
        "prep_time": None,
        "cook_time": None,
        "total_time": None,
        "servings": None,
        "image_url": None,
        "source": url,
        "notes": None,
    }

    # SSRF protection: validate the URL before making any server-side request.
    # SSRFError is intentionally not caught here so it propagates to the caller.
    validate_url(url)

    try:
        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=15.0,
            headers={"User-Agent": _BROWSER_UA},
            event_hooks={"response": [_check_redirect]},
        )
        response.raise_for_status()
        try:
            scraper = scrape_html(response.text, org_url=url)
        except Exception:
            # Site not explicitly supported — fall back to wild mode (JSON-LD/schema.org)
            scraper = scrape_html(response.text, org_url=url, wild_mode=True)
    except SSRFError:
        raise
    except Exception as e:
        # Direct fetch failed (e.g. 403) — let recipe_scrapers fetch the page itself
        logger.info(f"Direct fetch failed for {url}, trying online mode: {e}")
        try:
            scraper = scrape_html(None, org_url=url, online=True)
        except Exception as e2:
            logger.error(f"Failed to scrape {url}: {e2}")
            return result

    try:
        result["title"] = scraper.title()
    except Exception:
        pass

    try:
        result["ingredients"] = scraper.ingredients()
    except Exception:
        pass

    try:
        raw_instructions = scraper.instructions()
        if raw_instructions:
            result["instructions"] = [
                s.strip() for s in raw_instructions.split("\n") if s.strip()
            ]
    except Exception:
        pass

    try:
        prep = scraper.prep_time()
        if prep:
            result["prep_time"] = f"{prep}min"
    except Exception:
        pass

    try:
        cook = scraper.cook_time()
        if cook:
            result["cook_time"] = f"{cook}min"
    except Exception:
        pass

    try:
        total = scraper.total_time()
        if total:
            result["total_time"] = f"{total}min"
    except Exception:
        pass

    try:
        result["servings"] = str(scraper.yields())
    except Exception:
        pass

    try:
        image = scraper.image()
        if image:
            result["image_url"] = _upgrade_image_url(image)
    except Exception:
        pass

    try:
        author = scraper.author()
        if author:
            result["author"] = author
    except Exception:
        pass

    return result


def _upgrade_image_url(url: str) -> str:
    """Try to get the full-size image URL instead of a thumbnail.

    WordPress sites often serve thumbnails with dimension suffixes like
    '-225x225.jpg'. Stripping the suffix gives the full-size original.
    """
    upgraded = re.sub(r"-\d+x\d+(\.\w+)$", r"\1", url)
    if upgraded != url:
        try:
            resp = httpx.head(
                upgraded,
                follow_redirects=True,
                timeout=5.0,
                headers={"User-Agent": _BROWSER_UA},
                event_hooks={"response": [_check_redirect]},
            )
            if resp.status_code == 200:
                return upgraded
        except Exception:
            pass
    return url


def download_image(image_url: str, save_path: Path) -> bool:
    """Download an image from a URL and save it to disk."""
    # SSRF protection: validate the URL before fetching.
    try:
        validate_url(image_url)
    except SSRFError as e:
        logger.warning(f"SSRF check blocked image URL '{image_url}': {e}")
        return False

    try:
        response = httpx.get(
            image_url,
            follow_redirects=True,
            timeout=15.0,
            headers={"User-Agent": _BROWSER_UA},
            event_hooks={"response": [_check_redirect]},
        )
        response.raise_for_status()

        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(response.content)
        logger.info(f"Downloaded image to {save_path}")
        return True
    except SSRFError as e:
        logger.warning(f"SSRF check blocked redirect for '{image_url}': {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to download image from {image_url}: {e}")
        return False
