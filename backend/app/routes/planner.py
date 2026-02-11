import datetime
import logging
from pathlib import Path
from typing import Dict, List, Optional

import frontmatter
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.git import git_commit
from app.remote_config import load_config

logger = logging.getLogger(__name__)


class MealSlot(BaseModel):
    slug: str
    fork: Optional[str] = None


class SavePlanRequest(BaseModel):
    weeks: Dict[str, List[MealSlot]]


class AddMealRequest(BaseModel):
    slug: str
    fork: Optional[str] = None


def _week_key_for_date(date_str: str) -> str:
    """Return ISO week key like '2026-W07' for a date string 'YYYY-MM-DD'."""
    d = datetime.date.fromisoformat(date_str)
    year, week, _ = d.isocalendar()
    return f"{year}-W{week:02d}"


def create_planner_router(recipes_dir: Path, config_path: Path) -> APIRouter:
    router = APIRouter(prefix="/api/meal-plan")

    def _plan_dir() -> Path:
        d = recipes_dir / "meal-plans"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _week_path(week_key: str) -> Path:
        return _plan_dir() / f"{week_key}.md"

    def _load_week(week_key: str) -> dict:
        path = _week_path(week_key)
        if not path.exists():
            return {}
        try:
            post = frontmatter.load(path)
            return post.metadata.get("days", {})
        except Exception:
            logger.exception("Failed to load meal plan week %s", week_key)
            return {}

    def _save_week(week_key: str, days: dict) -> None:
        path = _week_path(week_key)

        # Remove empty days
        days = {d: meals for d, meals in days.items() if meals}

        if not days:
            # Delete the file if no meals remain
            if path.exists():
                path.unlink()
            return

        post = frontmatter.Post(content="", **{"week": week_key, "days": days})

        # Generate human-readable body
        lines = [f"# Meal Plan — {week_key}\n"]
        for day in sorted(days.keys()):
            meals = days[day]
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

        # Conditionally git-commit based on sync_meal_plans setting
        try:
            _, sync_cfg = load_config(config_path)
            if sync_cfg.sync_meal_plans:
                git_commit(recipes_dir, path, f"Update meal plan {week_key}")
        except Exception:
            logger.exception("Failed to check sync config for meal plan commit")

    @router.get("")
    def get_meal_plan(week: Optional[str] = None):
        """Get meal plan for a week. Param like '2026-W07', defaults to current week."""
        if not week:
            today = datetime.date.today()
            year, wk, _ = today.isocalendar()
            week = f"{year}-W{wk:02d}"

        try:
            parts = week.split("-W")
            year = int(parts[0])
            week_num = int(parts[1])
            monday = datetime.date.fromisocalendar(year, week_num, 1)
        except (ValueError, IndexError):
            return {"weeks": {}}

        date_range = [(monday + datetime.timedelta(days=i)).isoformat() for i in range(7)]
        stored = _load_week(week)

        result = {}
        for d in date_range:
            result[d] = stored.get(d, [])

        return {"weeks": result}

    @router.put("")
    def save_meal_plan(data: SavePlanRequest):
        """Save meal plan. Groups dates by ISO week and saves each week file."""
        # Group incoming dates by week
        by_week: Dict[str, Dict[str, list]] = {}
        for day, meals in data.weeks.items():
            wk = _week_key_for_date(day)
            if wk not in by_week:
                by_week[wk] = {}
            serialized = []
            for meal in meals:
                entry = {"slug": meal.slug}
                if meal.fork:
                    entry["fork"] = meal.fork
                serialized.append(entry)
            by_week[wk][day] = serialized

        # Load, merge, and save each affected week
        all_days = {}
        for wk, new_days in by_week.items():
            existing = _load_week(wk)
            for day, meals in new_days.items():
                if meals:
                    existing[day] = meals
                elif day in existing:
                    del existing[day]
            _save_week(wk, existing)
            all_days.update(existing)

        return {"weeks": all_days}

    @router.post("/{date}")
    def add_meal_to_day(date: str, meal: AddMealRequest):
        """Add a meal to a specific date."""
        try:
            datetime.date.fromisoformat(date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")

        week_key = _week_key_for_date(date)
        days = _load_week(week_key)
        day_meals = days.get(date, [])
        entry: dict = {"slug": meal.slug}
        if meal.fork:
            entry["fork"] = meal.fork
        day_meals.append(entry)
        days[date] = day_meals
        _save_week(week_key, days)
        return {"date": date, "meals": days.get(date, [])}

    @router.delete("/{date}")
    def clear_day(date: str):
        """Clear all meals for a specific date."""
        try:
            datetime.date.fromisoformat(date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")

        week_key = _week_key_for_date(date)
        days = _load_week(week_key)
        if date in days:
            del days[date]
        _save_week(week_key, days)
        return {"date": date, "meals": []}

    @router.delete("/{date}/{meal_index}")
    def remove_meal_from_day(date: str, meal_index: int):
        """Remove a specific meal by index from a date."""
        try:
            datetime.date.fromisoformat(date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")

        week_key = _week_key_for_date(date)
        days = _load_week(week_key)
        day_meals = days.get(date, [])
        if meal_index < 0 or meal_index >= len(day_meals):
            raise HTTPException(status_code=404, detail="Meal index out of range")
        day_meals.pop(meal_index)
        days[date] = day_meals
        _save_week(week_key, days)
        return {"date": date, "meals": days.get(date, [])}

    return router
