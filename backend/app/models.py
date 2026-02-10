from typing import List, Optional

from pydantic import BaseModel


class ForkSummary(BaseModel):
    name: str
    fork_name: str
    author: Optional[str] = None
    date_added: Optional[str] = None
    merged_at: Optional[str] = None
    forked_at_commit: Optional[str] = None


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
    image: Optional[str] = None
    forks: List[ForkSummary] = []
    cook_history: List[CookHistoryEntry] = []


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


class SyncStatus(BaseModel):
    connected: bool = False
    last_synced: Optional[str] = None
    ahead: int = 0
    behind: int = 0
    error: Optional[str] = None


class StreamEvent(BaseModel):
    type: str  # "created", "edited", "forked", "merged"
    date: str
    message: str
    commit: Optional[str] = None
    fork_name: Optional[str] = None
    fork_slug: Optional[str] = None


class RemoteConfig(BaseModel):
    provider: Optional[str] = None  # "github", "gitlab", "generic"
    url: Optional[str] = None
    token: Optional[str] = None


class SyncConfig(BaseModel):
    enabled: bool = False
    interval_seconds: int = 90
