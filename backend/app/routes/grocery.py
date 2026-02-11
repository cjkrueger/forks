"""Server-side grocery list API."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.ingredients import parse_ingredient, ingredient_key, format_quantity
from app.models import AddToGroceryRequest, GroceryItem, GroceryList, GroceryRecipe

logger = logging.getLogger(__name__)


def create_grocery_router(recipes_dir: Path) -> APIRouter:
    router = APIRouter(prefix="/api/grocery")
    grocery_path = recipes_dir / "grocery-list.json"

    def _load() -> GroceryList:
        if not grocery_path.exists():
            return GroceryList()
        try:
            data = json.loads(grocery_path.read_text())
            return GroceryList(**data)
        except Exception:
            logger.exception("Failed to load grocery list")
            return GroceryList()

    def _save(store: GroceryList) -> None:
        grocery_path.write_text(json.dumps(store.model_dump(), indent=2))

    @router.get("")
    def get_grocery_list():
        return _load().model_dump()

    @router.post("/recipes")
    def add_recipe_to_grocery(req: AddToGroceryRequest):
        store = _load()
        items = []
        for line in req.ingredients:
            parsed = parse_ingredient(line)
            items.append(GroceryItem(**parsed))
        store.recipes[req.slug] = GroceryRecipe(
            title=req.title,
            fork=req.fork,
            servings=req.servings,
            items=items,
        )
        _save(store)
        return store.model_dump()

    @router.delete("/recipes/{slug}")
    def remove_recipe_from_grocery(slug: str):
        store = _load()
        if slug in store.recipes:
            del store.recipes[slug]
            _save(store)
        return store.model_dump()

    @router.post("/check/{item_key:path}")
    def toggle_checked(item_key: str):
        store = _load()
        if item_key in store.checked:
            store.checked.remove(item_key)
        else:
            store.checked.append(item_key)
        _save(store)
        return store.model_dump()

    @router.delete("/items/{item_key:path}")
    def remove_item(item_key: str):
        store = _load()
        # Remove the item from all recipes
        empty_slugs = []
        for slug, recipe in store.recipes.items():
            recipe.items = [
                item for item in recipe.items
                if ingredient_key(item.model_dump()) != item_key
            ]
            if not recipe.items:
                empty_slugs.append(slug)
        for slug in empty_slugs:
            del store.recipes[slug]
        store.checked = [k for k in store.checked if k != item_key]
        _save(store)
        return store.model_dump()

    @router.delete("/checked")
    def clear_checked():
        store = _load()
        store.checked = []
        _save(store)
        return store.model_dump()

    @router.delete("")
    def clear_all():
        store = GroceryList()
        _save(store)
        return store.model_dump()

    @router.get("/export")
    def export_grocery():
        store = _load()
        # Merge items across recipes
        merged: dict = {}
        for recipe in store.recipes.values():
            for item in recipe.items:
                key = ingredient_key(item.model_dump())
                if key in merged:
                    existing = merged[key]
                    if existing["quantity"] is not None and item.quantity is not None and existing["unit"] == item.unit:
                        existing["quantity"] += item.quantity
                else:
                    merged[key] = {
                        "quantity": item.quantity,
                        "unit": item.unit,
                        "name": item.name,
                        "displayText": item.displayText,
                    }

        unchecked_lines = []
        checked_lines = []
        for key, val in sorted(merged.items(), key=lambda kv: kv[1]["name"]):
            qty_str = format_quantity(val["quantity"]) if val["quantity"] is not None else ""
            unit_str = val["unit"] or ""
            display = " ".join(filter(None, [qty_str, unit_str, val["name"]]))
            if key in store.checked:
                checked_lines.append(f"[x] {display}")
            else:
                unchecked_lines.append(f"[ ] {display}")

        lines = []
        if unchecked_lines:
            lines.append("To buy:")
            lines.extend(unchecked_lines)
        if checked_lines:
            if lines:
                lines.append("")
            lines.append("Got it:")
            lines.extend(checked_lines)

        if not lines:
            lines.append("Grocery list is empty.")

        return PlainTextResponse(
            content="\n".join(lines) + "\n",
            headers={"Content-Disposition": 'attachment; filename="grocery-list.txt"'},
        )

    return router
