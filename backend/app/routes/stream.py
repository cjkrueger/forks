"""API route for recipe stream/timeline visualization."""

import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException

from app.index import RecipeIndex
from app.models import StreamEvent

logger = logging.getLogger(__name__)


def create_stream_router(index: RecipeIndex, recipes_dir: Path) -> APIRouter:
    router = APIRouter()

    @router.get("/api/recipes/{slug}/stream")
    def get_stream(slug: str):
        recipe = index.get(slug)
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")

        events: List[StreamEvent] = []

        # Build events from the recipe's own changelog
        for entry in recipe.changelog:
            events.append(StreamEvent(
                type=entry.action,
                date=entry.date,
                message=entry.summary,
            ))

        # Build events from fork changelogs
        for fork_summary in recipe.forks:
            for entry in fork_summary.changelog:
                # Map "created" action on a fork to "forked" event type
                event_type = "forked" if entry.action == "created" else entry.action
                events.append(StreamEvent(
                    type=event_type,
                    date=entry.date,
                    message=entry.summary,
                    fork_name=fork_summary.fork_name,
                    fork_slug=fork_summary.name,
                ))

        events.sort(key=lambda e: e.date)
        return {"events": [e.model_dump() for e in events]}

    return router
