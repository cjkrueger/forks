"""API route for recipe stream/timeline visualization."""

import logging
import re
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException

from app.index import RecipeIndex
from app.models import StreamEvent
from app.slug_utils import validate_slug

logger = logging.getLogger(__name__)

_FORK_NAME_RE = re.compile(r"(?:Merged|Unmerged) fork '(.+)'")


def create_stream_router(index: RecipeIndex, recipes_dir: Path) -> APIRouter:
    router = APIRouter()

    @router.get("/api/recipes/{slug}/stream")
    def get_stream(slug: str):
        validate_slug(slug)
        recipe = index.get(slug)
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")

        # Build lookup from fork display name -> fork slug
        fork_slug_lookup = {f.fork_name: f.name for f in recipe.forks}

        events: List[StreamEvent] = []

        # Build events from the recipe's own changelog
        for entry in recipe.changelog:
            ev = StreamEvent(
                type=entry.action,
                date=entry.date,
                message=entry.summary,
            )
            # Enrich merge/unmerge events with structured fork info;
            # skip events for forks that no longer exist (deleted)
            if entry.action in ("merged", "unmerged"):
                m = _FORK_NAME_RE.search(entry.summary)
                if m:
                    fname = m.group(1)
                    slug = fork_slug_lookup.get(fname)
                    if slug is None:
                        continue
                    ev.fork_name = fname
                    ev.fork_slug = slug
            events.append(ev)

        # Build events from fork changelogs
        for fork_summary in recipe.forks:
            for entry in fork_summary.changelog:
                # Skip fork-side merge/unmerge — base recipe events are canonical
                if entry.action in ("merged", "unmerged"):
                    continue
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
