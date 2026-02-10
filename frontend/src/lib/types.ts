export interface RecipeSummary {
  slug: string;
  title: string;
  tags: string[];
  servings: string | null;
  prep_time: string | null;
  cook_time: string | null;
  date_added: string | null;
  source: string | null;
  image: string | null;
}

export interface Recipe extends RecipeSummary {
  content: string;
}

export interface ScrapeResponse {
  title: string | null;
  ingredients: string[];
  instructions: string[];
  prep_time: string | null;
  cook_time: string | null;
  total_time: string | null;
  servings: string | null;
  image_url: string | null;
  source: string;
  notes: string | null;
}

export interface RecipeInput {
  title: string;
  tags: string[];
  servings: string | null;
  prep_time: string | null;
  cook_time: string | null;
  source: string | null;
  image: string | null;
  ingredients: string[];
  instructions: string[];
  notes: string[];
}
