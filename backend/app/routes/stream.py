"""API route for recipe stream/timeline visualization."""

import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException

from app.git import git_log
from app.index import RecipeIndex
from app.models import StreamEvent

logger = logging.getLogger(__name__)

_NOISE_PREFIXES = ("Log cook", "Add favorite", "Remove favorite", "Delete cook")


def create_stream_router(index: RecipeIndex, recipes_dir: Path) -> APIRouter:
    router = APIRouter()

    @router.get("/api/recipes/{slug}/stream")
    def get_stream(slug: str):
        recipe = index.get(slug)
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")

        events: List[StreamEvent] = []

        base_path = recipes_dir / f"{slug}.md"
        if base_path.exists():
            log_entries = git_log(recipes_dir, base_path, max_entries=50)
            for entry in log_entries:
                msg = entry["message"]
                if any(msg.startswith(prefix) for prefix in _NOISE_PREFIXES):
                    continue
                if msg.startswith("Create recipe") or msg == "Initial commit":
                    event_type = "created"
                elif msg.startswith("Merge fork"):
                    event_type = "merged"
                    fork_name = None
                    if "'" in msg:
                        fork_name = msg.split("'")[1]
                    events.append(StreamEvent(
                        type=event_type, date=entry["date"], message=msg,
                        commit=entry["hash"], fork_name=fork_name,
                    ))
                    continue
                else:
                    event_type = "edited"
                events.append(StreamEvent(
                    type=event_type, date=entry["date"], message=msg, commit=entry["hash"],
                ))

        for fork_summary in recipe.forks:
            if fork_summary.date_added:
                events.append(StreamEvent(
                    type="forked", date=fork_summary.date_added,
                    message=f"Forked: {fork_summary.fork_name}",
                    fork_name=fork_summary.fork_name, fork_slug=fork_summary.name,
                ))
            if fork_summary.merged_at:
                has_merge = any(
                    e.type == "merged" and e.fork_name == fork_summary.fork_name
                    for e in events
                )
                if not has_merge:
                    events.append(StreamEvent(
                        type="merged", date=fork_summary.merged_at,
                        message=f"Merged: {fork_summary.fork_name}",
                        fork_name=fork_summary.fork_name, fork_slug=fork_summary.name,
                    ))

        events.sort(key=lambda e: e.date)
        return {"events": [e.model_dump() for e in events]}

    return router
