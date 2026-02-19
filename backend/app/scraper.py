import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

import httpx
from recipe_scrapers import scrape_html
from recipe_scrapers._exceptions import (
    ElementNotFoundInHtml,
    NoSchemaFoundInWildMode,
    OpenGraphException,
    RecipeScrapersExceptions,
    SchemaOrgException,
    WebsiteNotImplementedError,
)

logger = logging.getLogger(__name__)

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Exceptions raised by recipe_scrapers when a field is unavailable or unparseable.
_SCRAPER_FIELD_ERRORS = (
    ElementNotFoundInHtml,
    NoSchemaFoundInWildMode,
    OpenGraphException,
    SchemaOrgException,
    RecipeScrapersExceptions,
    ValueError,
    AttributeError,
    KeyError,
)


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

    try:
        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=15.0,
            headers={"User-Agent": _BROWSER_UA},
        )
        response.raise_for_status()
        try:
            scraper = scrape_html(response.text, org_url=url)
        except WebsiteNotImplementedError:
            # Site not explicitly supported — fall back to wild mode (JSON-LD/schema.org)
            logger.debug("Site not in scraper database for %s, trying wild mode", url)
            scraper = scrape_html(response.text, org_url=url, wild_mode=True)
    except (httpx.HTTPStatusError, httpx.RequestError, httpx.InvalidURL) as e:
        # Direct fetch failed (e.g. 403, connection refused, bad URL) — let
        # recipe_scrapers fetch the page itself via its online mode.
        logger.info("Direct fetch failed for %s, trying online mode: %s", url, e)
        try:
            scraper = scrape_html(None, org_url=url, online=True)
        except (httpx.RequestError, RecipeScrapersExceptions) as e2:
            logger.error("Failed to scrape %s: %s", url, e2)
            return result

    try:
        result["title"] = scraper.title()
    except _SCRAPER_FIELD_ERRORS as e:
        logger.debug("Could not extract title from %s: %s", url, e)

    try:
        result["ingredients"] = scraper.ingredients()
    except _SCRAPER_FIELD_ERRORS as e:
        logger.debug("Could not extract ingredients from %s: %s", url, e)

    try:
        raw_instructions = scraper.instructions()
        if raw_instructions:
            result["instructions"] = [
                s.strip() for s in raw_instructions.split("\n") if s.strip()
            ]
    except _SCRAPER_FIELD_ERRORS as e:
        logger.debug("Could not extract instructions from %s: %s", url, e)

    try:
        prep = scraper.prep_time()
        if prep:
            result["prep_time"] = f"{prep}min"
    except _SCRAPER_FIELD_ERRORS as e:
        logger.debug("Could not extract prep_time from %s: %s", url, e)

    try:
        cook = scraper.cook_time()
        if cook:
            result["cook_time"] = f"{cook}min"
    except _SCRAPER_FIELD_ERRORS as e:
        logger.debug("Could not extract cook_time from %s: %s", url, e)

    try:
        total = scraper.total_time()
        if total:
            result["total_time"] = f"{total}min"
    except _SCRAPER_FIELD_ERRORS as e:
        logger.debug("Could not extract total_time from %s: %s", url, e)

    try:
        result["servings"] = str(scraper.yields())
    except _SCRAPER_FIELD_ERRORS as e:
        logger.debug("Could not extract servings from %s: %s", url, e)

    try:
        image = scraper.image()
        if image:
            result["image_url"] = _upgrade_image_url(image)
    except _SCRAPER_FIELD_ERRORS as e:
        logger.debug("Could not extract image from %s: %s", url, e)

    try:
        author = scraper.author()
        if author:
            result["author"] = author
    except _SCRAPER_FIELD_ERRORS as e:
        logger.debug("Could not extract author from %s: %s", url, e)

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
            )
            if resp.status_code == 200:
                return upgraded
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.debug("Could not verify upgraded image URL %s: %s", upgraded, e)
    return url


def download_image(image_url: str, save_path: Path) -> bool:
    """Download an image from a URL and save it to disk."""
    try:
        response = httpx.get(
            image_url,
            follow_redirects=True,
            timeout=15.0,
            headers={"User-Agent": _BROWSER_UA},
        )
        response.raise_for_status()

        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(response.content)
        logger.info("Downloaded image to %s", save_path)
        return True
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        logger.error("Failed to download image from %s: %s (network/HTTP error)", image_url, e)
        return False
    except OSError as e:
        logger.error("Failed to save image to %s: %s (file system error)", save_path, e)
        return False
