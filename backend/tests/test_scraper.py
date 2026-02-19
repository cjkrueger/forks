from pathlib import Path
from unittest.mock import patch, MagicMock

import httpx
from recipe_scrapers._exceptions import (
    ElementNotFoundInHtml,
    RecipeScrapersExceptions,
)

from app.scraper import scrape_recipe, download_image


def _make_mock_scraper(
    title="Test Recipe",
    ingredients=None,
    instructions="Step one\nStep two\nStep three",
    prep_time=10,
    cook_time=25,
    total_time=35,
    yields="4 servings",
    image="https://example.com/image.jpg",
    author="Test Author",
):
    """Create a mock scraper object with configurable return values."""
    scraper = MagicMock()
    scraper.title.return_value = title
    scraper.ingredients.return_value = ingredients or ["1 cup flour", "2 eggs", "1 tsp salt"]
    scraper.instructions.return_value = instructions
    scraper.prep_time.return_value = prep_time
    scraper.cook_time.return_value = cook_time
    scraper.total_time.return_value = total_time
    scraper.yields.return_value = yields
    scraper.image.return_value = image
    scraper.author.return_value = author
    return scraper


@patch("app.scraper.scrape_html")
@patch("app.scraper.httpx.get")
def test_scrape_recipe_with_mock(mock_get, mock_scrape_html):
    """Full successful scrape returns all fields populated."""
    mock_response = MagicMock()
    mock_response.text = "<html>recipe page</html>"
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    mock_scraper = _make_mock_scraper()
    mock_scrape_html.return_value = mock_scraper

    result = scrape_recipe("https://example.com/recipe")

    assert result["title"] == "Test Recipe"
    assert result["author"] == "Test Author"
    assert result["ingredients"] == ["1 cup flour", "2 eggs", "1 tsp salt"]
    assert result["instructions"] == ["Step one", "Step two", "Step three"]
    assert result["prep_time"] == "10min"
    assert result["cook_time"] == "25min"
    assert result["total_time"] == "35min"
    assert result["servings"] == "4 servings"
    assert result["image_url"] == "https://example.com/image.jpg"
    assert result["source"] == "https://example.com/recipe"

    mock_get.assert_called_once_with(
        "https://example.com/recipe",
        follow_redirects=True,
        timeout=15.0,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"},
    )
    mock_scrape_html.assert_called_once_with(
        "<html>recipe page</html>", org_url="https://example.com/recipe"
    )


@patch("app.scraper.scrape_html")
@patch("app.scraper.httpx.get")
def test_scrape_recipe_handles_failure(mock_get, mock_scrape_html):
    """Network failure falls back to online mode; if that also fails, returns empty result."""
    mock_get.side_effect = httpx.ConnectError("Connection refused")
    # Use a specific RecipeScrapersExceptions subclass to reflect real failure modes
    mock_scrape_html.side_effect = RecipeScrapersExceptions("Online mode also failed")

    result = scrape_recipe("https://bad-url.example.com/recipe")

    assert result["title"] is None
    assert result["author"] is None
    assert result["ingredients"] == []
    assert result["instructions"] == []
    assert result["prep_time"] is None
    assert result["cook_time"] is None
    assert result["total_time"] is None
    assert result["servings"] is None
    assert result["image_url"] is None
    assert result["source"] == "https://bad-url.example.com/recipe"
    assert result["notes"] is None


@patch("app.scraper.scrape_html")
@patch("app.scraper.httpx.get")
def test_scrape_recipe_handles_partial_data(mock_get, mock_scrape_html):
    """Scraper that only has title and ingredients still returns partial data."""
    mock_response = MagicMock()
    mock_response.text = "<html>partial recipe</html>"
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    scraper = MagicMock()
    scraper.title.return_value = "Partial Recipe"
    scraper.ingredients.return_value = ["some ingredient"]
    # Use specific exception types that the scraper actually raises for missing fields
    scraper.instructions.side_effect = ElementNotFoundInHtml("instructions")
    scraper.prep_time.side_effect = ElementNotFoundInHtml("prep_time")
    scraper.cook_time.side_effect = ElementNotFoundInHtml("cook_time")
    scraper.total_time.side_effect = ElementNotFoundInHtml("total_time")
    scraper.yields.side_effect = ElementNotFoundInHtml("yields")
    scraper.image.side_effect = ElementNotFoundInHtml("image")
    scraper.author.side_effect = ElementNotFoundInHtml("author")
    mock_scrape_html.return_value = scraper

    result = scrape_recipe("https://example.com/partial")

    assert result["title"] == "Partial Recipe"
    assert result["author"] is None
    assert result["ingredients"] == ["some ingredient"]
    assert result["instructions"] == []
    assert result["prep_time"] is None
    assert result["cook_time"] is None
    assert result["total_time"] is None
    assert result["servings"] is None
    assert result["image_url"] is None
    assert result["source"] == "https://example.com/partial"


@patch("app.scraper.httpx.get")
def test_download_image_success(mock_get, tmp_path):
    """Successful image download saves file and returns True."""
    fake_image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    mock_response = MagicMock()
    mock_response.content = fake_image_bytes
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    save_path = tmp_path / "images" / "recipe.png"
    result = download_image("https://example.com/photo.png", save_path)

    assert result is True
    assert save_path.exists()
    assert save_path.read_bytes() == fake_image_bytes

    mock_get.assert_called_once_with(
        "https://example.com/photo.png",
        follow_redirects=True,
        timeout=15.0,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"},
    )


@patch("app.scraper.httpx.get")
def test_download_image_failure(mock_get, tmp_path):
    """Failed image download returns False without crashing."""
    mock_get.side_effect = httpx.ConnectError("Connection refused")

    save_path = tmp_path / "images" / "recipe.png"
    result = download_image("https://bad-url.example.com/photo.png", save_path)

    assert result is False
    assert not save_path.exists()
