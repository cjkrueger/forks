export interface CookHistoryEntry {
  date: string;
  fork: string | null;
}

export interface ForkSummary {
  name: string;
  fork_name: string;
  author: string | null;
  date_added: string | null;
}

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
  forks: ForkSummary[];
  cook_history: CookHistoryEntry[];
}

export interface Recipe extends RecipeSummary {
  content: string;
}

export interface ForkDetail extends ForkSummary {
  content: string;
}

export interface ForkInput {
  fork_name: string;
  author: string | null;
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

export interface ScrapeResponse {
  title: string | null;
  tags: string[];
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
