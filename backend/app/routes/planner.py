import datetime
import logging
from pathlib import Path
from typing import Dict, List, Optional

import frontmatter
from fastapi import APIRouter
from pydantic import BaseModel

from app.git import git_commit

logger = logging.getLogger(__name__)


class MealSlot(BaseModel):
    slug: str
    fork: Optional[str] = None


class SavePlanRequest(BaseModel):
    weeks: Dict[str, List[MealSlot]]


def create_planner_router(recipes_dir: Path) -> APIRouter:
    router = APIRouter(prefix="/api/meal-plan")

    def _plan_path() -> Path:
        return recipes_dir / "meal-plan.md"

    def _load_plan() -> dict:
        path = _plan_path()
        if not path.exists():
            return {}
        try:
            post = frontmatter.load(path)
            return post.metadata.get("weeks", {})
        except Exception:
            logger.exception("Failed to load meal plan")
            return {}

    def _save_plan(weeks: dict) -> None:
        path = _plan_path()
        post = frontmatter.Post(content="", **{"weeks": weeks})

        # Generate human-readable body
        lines = ["# Meal Plan\n"]
        for day in sorted(weeks.keys()):
            meals = weeks[day]
            if meals:
                lines.append(f"## {day}\n")
                for meal in meals:
                    slug = meal if isinstance(meal, str) else meal.get("slug", "")
                    fork = None if isinstance(meal, str) else meal.get("fork")
                    if fork:
                        lines.append(f"- {slug} (fork: {fork})")
                    else:
                        lines.append(f"- {slug}")
                lines.append("")

        post.content = "\n".join(lines)
        path.write_text(frontmatter.dumps(post))
        git_commit(recipes_dir, path, "Update meal plan")

    @router.get("")
    def get_meal_plan(week: Optional[str] = None):
        """Get meal plan. Optional week param like '2026-W07' filters to that week's Mon-Sun."""
        weeks = _load_plan()

        if week:
            try:
                parts = week.split("-W")
                year = int(parts[0])
                week_num = int(parts[1])
                monday = datetime.date.fromisocalendar(year, week_num, 1)
                date_range = [(monday + datetime.timedelta(days=i)).isoformat() for i in range(7)]
                filtered = {}
                for d in date_range:
                    if d in weeks:
                        filtered[d] = weeks[d]
                    else:
                        filtered[d] = []
                return {"weeks": filtered}
            except (ValueError, IndexError):
                pass

        return {"weeks": weeks}

    @router.put("")
    def save_meal_plan(data: SavePlanRequest):
        """Save the entire meal plan. Merges with existing data."""
        existing = _load_plan()

        for day, meals in data.weeks.items():
            serialized = []
            for meal in meals:
                entry = {"slug": meal.slug}
                if meal.fork:
                    entry["fork"] = meal.fork
                serialized.append(entry)
            if serialized:
                existing[day] = serialized
            elif day in existing:
                del existing[day]

        _save_plan(existing)
        return {"weeks": existing}

    return router
