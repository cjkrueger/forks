from pydantic import BaseModel


class RecipeSummary(BaseModel):
    slug: str
    title: str
    tags: list[str] = []
    servings: str | None = None
    prep_time: str | None = None
    cook_time: str | None = None
    date_added: str | None = None
    source: str | None = None
    image: str | None = None


class Recipe(RecipeSummary):
    content: str
