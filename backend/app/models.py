from typing import List, Optional

from pydantic import BaseModel


class ForkSummary(BaseModel):
    name: str
    fork_name: str
    author: Optional[str] = None
    date_added: Optional[str] = None


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
