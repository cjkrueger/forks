"""Simple keyword-based auto-tagger for scraped recipes."""

from typing import List

# Proteins
PROTEINS = {
    "chicken": ["chicken"],
    "beef": ["beef", "chuck roast", "ground beef", "steak", "brisket", "short rib"],
    "pork": ["pork", "bacon", "pancetta", "guanciale", "ham", "prosciutto", "sausage"],
    "shrimp": ["shrimp", "prawn"],
    "salmon": ["salmon"],
    "fish": ["cod", "tilapia", "halibut", "tuna", "mahi", "snapper", "trout", "catfish"],
    "lamb": ["lamb"],
    "turkey": ["turkey"],
    "tofu": ["tofu", "tempeh"],
}

# Meal types
MEAL_TYPES = {
    "soup": ["soup", "chowder", "bisque", "broth"],
    "stew": ["stew", "braised"],
    "salad": ["salad", "slaw"],
    "pasta": ["pasta", "spaghetti", "penne", "rigatoni", "linguine", "fettuccine",
              "lasagna", "macaroni", "noodle", "carbonara", "bolognese"],
    "tacos": ["taco", "tacos"],
    "curry": ["curry", "tikka masala", "korma", "vindaloo"],
    "stir-fry": ["stir fry", "stir-fry", "stir fried"],
    "sandwich": ["sandwich", "burger", "wrap", "sub"],
    "pizza": ["pizza", "flatbread"],
    "casserole": ["casserole", "bake"],
    "roast": ["roast", "roasted"],
    "grilled": ["grill", "grilled"],
    "fried": ["fried", "fritter", "fry"],
    "baked": ["baked", "baking"],
    "dessert": ["cake", "cookie", "brownie", "muffin", "cupcake",
                "pudding", "tart", "cheesecake", "ice cream", "cobbler", "crisp"],
    "breakfast": ["breakfast", "pancake", "waffle", "omelet", "omelette",
                  "french toast", "scramble", "hash"],
    "appetizer": ["appetizer", "dip", "bruschetta", "crostini"],
    "rice": ["rice", "risotto", "pilaf", "biryani", "fried rice"],
}

# Cuisine indicators (checked against title + ingredients)
CUISINES = {
    "mexican": ["tortilla", "salsa", "enchilada", "burrito", "taco", "chile",
                "chipotle", "jalapeño", "jalapeno", "guacamole", "queso",
                "birria", "carnitas", "cilantro lime"],
    "italian": ["parmesan", "parmigiano", "pecorino", "mozzarella", "ricotta",
                "marinara", "pesto", "prosciutto", "risotto", "bruschetta",
                "carbonara", "bolognese", "arrabbiata"],
    "thai": ["thai", "coconut milk", "fish sauce", "curry paste", "lemongrass",
             "thai basil", "pad thai", "tom kha", "tom yum"],
    "indian": ["garam masala", "turmeric", "tikka", "naan", "paneer",
               "biryani", "korma", "vindaloo", "masala", "tandoori", "dal"],
    "chinese": ["soy sauce", "hoisin", "wok", "szechuan", "sichuan",
                "kung pao", "lo mein", "chow mein", "dim sum", "dumpling"],
    "japanese": ["sushi", "teriyaki", "miso", "ramen", "udon", "soba",
                 "tempura", "ponzu", "wasabi", "edamame"],
    "korean": ["gochujang", "kimchi", "bibimbap", "bulgogi", "korean"],
    "french": ["gratin", "ratatouille", "béchamel", "bechamel",
               "au gratin", "confit", "bouillabaisse", "coq au vin", "crème brûlée",
               "quiche", "soufflé", "souffle", "cassoulet"],
    "mediterranean": ["feta", "hummus", "tahini", "tzatziki", "falafel",
                       "pita", "za'atar", "zaatar", "halloumi", "labneh",
                       "mediterranean"],
    "cajun": ["cajun", "creole", "jambalaya", "gumbo", "andouille", "étouffée"],
}

# Time-based tags
QUICK_THRESHOLD = 30  # minutes


def auto_tag(
    title: str,
    ingredients: List[str],
    prep_time: str = None,
    cook_time: str = None,
    total_time: str = None,
) -> List[str]:
    """Generate tags from recipe title, ingredients, and timing."""
    tags = []

    # Combine title and ingredients into searchable strings
    text = title.lower()
    ing_text = " ".join(ingredients).lower()
    all_text = f"{text} {ing_text}"

    # Ingredient terms that shouldn't trigger a protein tag
    PROTEIN_EXCLUDES = {"beef broth", "chicken broth", "chicken stock", "beef stock",
                        "fish sauce", "fish stock"}

    # Check proteins — match title freely, but filter false positives from ingredients
    for tag, keywords in PROTEINS.items():
        # Check title first (always reliable)
        if any(kw in text for kw in keywords):
            tags.append(tag)
            continue
        # Check ingredients, but skip if the match is only in an excluded compound
        ing_matches = [kw for kw in keywords if kw in ing_text]
        if ing_matches:
            # Make sure at least one match isn't part of an excluded compound
            real_match = any(
                not any(exc in ing_text and kw in exc for exc in PROTEIN_EXCLUDES)
                for kw in ing_matches
            )
            if real_match:
                tags.append(tag)

    # Check meal types (prefer title matches)
    for tag, keywords in MEAL_TYPES.items():
        if any(kw in text for kw in keywords):
            tags.append(tag)

    # Check cuisines (title + ingredients)
    for tag, keywords in CUISINES.items():
        if any(kw in all_text for kw in keywords):
            tags.append(tag)

    # Time-based tags
    total = _parse_minutes(total_time) or (_parse_minutes(prep_time) or 0) + (_parse_minutes(cook_time) or 0)
    if total and total <= QUICK_THRESHOLD:
        tags.append("quick")
    elif total and total >= 120:
        tags.append("weekend")

    return sorted(set(tags))


def _parse_minutes(time_str: str) -> int:
    """Parse a time string like '30min', '1hr', '90min' into minutes."""
    if not time_str:
        return 0
    time_str = time_str.lower().strip()
    try:
        # Handle plain numbers
        if time_str.isdigit():
            return int(time_str)
        # Handle '30min', '30 min'
        if "min" in time_str:
            return int(time_str.replace("min", "").replace(" ", ""))
        # Handle '1hr', '2hr'
        if "hr" in time_str:
            return int(time_str.replace("hr", "").replace(" ", "")) * 60
        return int(time_str)
    except (ValueError, TypeError):
        return 0
