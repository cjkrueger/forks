from typing import List, Optional

from pydantic import BaseModel


class ChangelogEntry(BaseModel):
    date: str
    action: str
    summary: str


class ForkSummary(BaseModel):
    name: str
    fork_name: str
    author: Optional[str] = None
    date_added: Optional[str] = None
    merged_at: Optional[str] = None
    forked_at_commit: Optional[str] = None
    version: int = 0
    changelog: List[ChangelogEntry] = []


class CookHistoryEntry(BaseModel):
    date: str
    fork: Optional[str] = None


class RecipeSummary(BaseModel):
    slug: str
    title: str
    tags: List[str] = []
    servings: Optional[str] = None
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    date_added: Optional[str] = None
    source: Optional[str] = None
    author: Optional[str] = None
    image: Optional[str] = None
    forks: List[ForkSummary] = []
    cook_history: List[CookHistoryEntry] = []
    likes: int = 0
    version: int = 0
    changelog: List[ChangelogEntry] = []


class Recipe(RecipeSummary):
    content: str


class ForkDetail(ForkSummary):
    content: str


class ForkInput(BaseModel):
    fork_name: str
    author: Optional[str] = None
    title: str
    tags: List[str] = []
    servings: Optional[str] = None
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    source: Optional[str] = None
    image: Optional[str] = None
    ingredients: List[str] = []
    instructions: List[str] = []
    notes: List[str] = []
    version: Optional[int] = None


class SyncStatus(BaseModel):
    connected: bool = False
    last_synced: Optional[str] = None
    ahead: int = 0
    behind: int = 0
    error: Optional[str] = None


class StreamEvent(BaseModel):
    type: str  # "created", "edited", "forked", "merged", "unmerged"
    date: str
    message: str
    commit: Optional[str] = None
    fork_name: Optional[str] = None
    fork_slug: Optional[str] = None


class RemoteConfig(BaseModel):
    provider: Optional[str] = None  # "github", "gitlab", "generic", "tangled", "local"
    url: Optional[str] = None
    token: Optional[str] = None
    local_path: Optional[str] = None


class SyncConfig(BaseModel):
    enabled: bool = False
    interval_seconds: int = 5400
    sync_meal_plans: bool = True
