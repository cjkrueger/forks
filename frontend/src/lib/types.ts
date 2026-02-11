export interface CookHistoryEntry {
  date: string;
  fork: string | null;
}

export interface ForkSummary {
  name: string;
  fork_name: string;
  author: string | null;
  date_added: string | null;
  merged_at: string | null;
  forked_at_commit: string | null;
  version: number;
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
  author: string | null;
  image: string | null;
  forks: ForkSummary[];
  cook_history: CookHistoryEntry[];
  likes: number;
  version: number;
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
  version?: number;
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
  author: string | null;
  notes: string | null;
}

export interface RecipeInput {
  title: string;
  tags: string[];
  servings: string | null;
  prep_time: string | null;
  cook_time: string | null;
  source: string | null;
  author?: string | null;
  image: string | null;
  ingredients: string[];
  instructions: string[];
  notes: string[];
  version?: number;
}

export interface MealSlot {
  slug: string;
  fork?: string | null;
}

export interface WeekPlan {
  [date: string]: MealSlot[];
}

export interface SyncStatus {
  connected: boolean;
  last_synced: string | null;
  ahead: number;
  behind: number;
  error: string | null;
}

export interface StreamEvent {
  type: 'created' | 'edited' | 'forked' | 'merged' | 'unmerged';
  date: string;
  message: string;
  commit: string | null;
  fork_name: string | null;
  fork_slug: string | null;
}

export interface StreamTimeline {
  events: StreamEvent[];
}

export interface RemoteConfig {
  provider: string | null;
  url: string | null;
  token: string | null;
  local_path: string | null;
}

export interface SyncConfig {
  enabled: boolean;
  interval_seconds: number;
  sync_meal_plans: boolean;
}

export interface AppSettings {
  remote: RemoteConfig;
  sync: SyncConfig;
}
