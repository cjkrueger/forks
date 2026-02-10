"""Tests for the auto-tagger module."""

from app.tagger import auto_tag, _parse_minutes


class TestAutoTag:
    def test_protein_from_title(self):
        tags = auto_tag("Chicken Noodle Soup", [])
        assert "chicken" in tags

    def test_protein_from_ingredients(self):
        tags = auto_tag("Hearty Stew", ["1 lb ground beef", "2 potatoes"])
        assert "beef" in tags

    def test_no_false_positive_from_broth(self):
        """'beef broth' or 'chicken broth' should not trigger protein tags."""
        tags = auto_tag("Vegetable Soup", ["2 cups beef broth", "3 carrots"])
        assert "beef" not in tags

    def test_no_false_positive_from_fish_sauce(self):
        tags = auto_tag("Pad Thai", ["2 tbsp fish sauce", "rice noodles"])
        assert "fish" not in tags

    def test_meal_type_from_title(self):
        tags = auto_tag("Chicken Noodle Soup", [])
        assert "soup" in tags

    def test_pasta_detected(self):
        tags = auto_tag("Spaghetti Bolognese", [])
        assert "pasta" in tags

    def test_cuisine_from_title(self):
        tags = auto_tag("Pad Thai with Shrimp", [])
        assert "thai" in tags

    def test_cuisine_from_ingredients(self):
        tags = auto_tag("Green Curry", ["coconut milk", "curry paste", "chicken"])
        assert "thai" in tags

    def test_mexican_cuisine(self):
        tags = auto_tag("Birria Tacos", ["chuck roast", "guajillo chile"])
        assert "mexican" in tags

    def test_italian_cuisine(self):
        tags = auto_tag("Pasta Carbonara", ["spaghetti", "guanciale", "pecorino"])
        assert "italian" in tags

    def test_quick_tag(self):
        tags = auto_tag("Quick Salad", [], total_time="15min")
        assert "quick" in tags

    def test_weekend_tag(self):
        tags = auto_tag("Slow Braised Short Ribs", [], total_time="180min")
        assert "weekend" in tags

    def test_time_from_prep_and_cook(self):
        tags = auto_tag("Quick Stir Fry", [], prep_time="10min", cook_time="10min")
        assert "quick" in tags

    def test_no_time_tag_for_medium_time(self):
        tags = auto_tag("Roasted Chicken", [], total_time="60min")
        assert "quick" not in tags
        assert "weekend" not in tags

    def test_tags_are_sorted_and_unique(self):
        tags = auto_tag("Chicken Chicken Soup", ["chicken"])
        assert tags == sorted(set(tags))

    def test_combined_example(self):
        """Full example: title + ingredients + time all contribute tags."""
        tags = auto_tag(
            "Birria Tacos",
            ["3 lb chuck roast", "guajillo chile", "tortillas"],
            total_time="180min",
        )
        assert "beef" in tags
        assert "tacos" in tags
        assert "mexican" in tags
        assert "weekend" in tags

    def test_dessert_detected(self):
        tags = auto_tag("Chocolate Brownie", [])
        assert "dessert" in tags

    def test_breakfast_detected(self):
        tags = auto_tag("Fluffy Pancakes", [])
        assert "breakfast" in tags

    def test_olive_oil_does_not_trigger_mediterranean(self):
        """Olive oil is too common to be a reliable mediterranean indicator."""
        tags = auto_tag("Roasted Vegetables", ["2 tbsp olive oil", "3 carrots", "1 onion"])
        assert "mediterranean" not in tags

    def test_mediterranean_from_specific_keywords(self):
        tags = auto_tag("Falafel Bowl", ["falafel", "tahini", "pita"])
        assert "mediterranean" in tags

    def test_empty_inputs(self):
        tags = auto_tag("", [])
        assert tags == []


class TestParseMinutes:
    def test_plain_number(self):
        assert _parse_minutes("30") == 30

    def test_minutes_suffix(self):
        assert _parse_minutes("30min") == 30

    def test_minutes_with_space(self):
        assert _parse_minutes("30 min") == 30

    def test_hours(self):
        assert _parse_minutes("2hr") == 120

    def test_none_input(self):
        assert _parse_minutes(None) == 0

    def test_empty_string(self):
        assert _parse_minutes("") == 0

    def test_invalid_string(self):
        assert _parse_minutes("abc") == 0
