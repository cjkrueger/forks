from typing import Dict, List, Optional

from pydantic import BaseModel

from app.enums import ChangelogAction, EventType, RemoteProvider


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
    failed_at: Optional[str] = None
    failed_reason: Optional[str] = None
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
    ingredients: List[str] = []
    instructions: List[str] = []
    notes: List[str] = []


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
    type: EventType
    date: str
    message: str
    commit: Optional[str] = None
    fork_name: Optional[str] = None
    fork_slug: Optional[str] = None


class RemoteConfig(BaseModel):
    provider: Optional[RemoteProvider] = None
    url: Optional[str] = None
    token: Optional[str] = None
    local_path: Optional[str] = None


class SyncConfig(BaseModel):
    enabled: bool = False
    interval_seconds: int = 5400
    sync_meal_plans: bool = True


class GroceryItem(BaseModel):
    quantity: Optional[float] = None
    unit: Optional[str] = None
    name: str
    displayText: str
    original: str


class GroceryRecipe(BaseModel):
    title: str
    fork: Optional[str] = None
    servings: Optional[str] = None
    items: List[GroceryItem] = []


class GroceryList(BaseModel):
    recipes: Dict[str, GroceryRecipe] = {}
    checked: List[str] = []


class AddToGroceryRequest(BaseModel):
    slug: str
    title: str
    ingredients: List[str]
    fork: Optional[str] = None
    servings: Optional[str] = None
