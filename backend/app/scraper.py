import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

import httpx
from recipe_scrapers import scrape_html

logger = logging.getLogger(__name__)


def scrape_recipe(url: str) -> Dict[str, Any]:
    """Scrape a recipe from a URL and return structured data."""
    result: Dict[str, Any] = {
        "title": None,
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
            headers={"User-Agent": "Mozilla/5.0 (compatible; Forks/1.0)"},
        )
        response.raise_for_status()
        scraper = scrape_html(response.text, org_url=url)
    except Exception as e:
        logger.error(f"Failed to scrape {url}: {e}")
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
        result["image_url"] = scraper.image()
    except Exception:
        pass

    return result


def download_image(image_url: str, save_path: Path) -> bool:
    """Download an image from a URL and save it to disk."""
    try:
        response = httpx.get(
            image_url,
            follow_redirects=True,
            timeout=15.0,
            headers={"User-Agent": "Mozilla/5.0 (compatible; Forks/1.0)"},
        )
        response.raise_for_status()

        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(response.content)
        logger.info(f"Downloaded image to {save_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to download image from {image_url}: {e}")
        return False
