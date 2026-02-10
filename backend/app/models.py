from typing import List, Optional

from pydantic import BaseModel


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


class Recipe(RecipeSummary):
    content: str
