"""Tests for the ingredient parser."""

from app.ingredients import parse_ingredient, ingredient_key, format_quantity


class TestParseIngredient:
    def test_simple_quantity_unit_name(self):
        result = parse_ingredient("2 cups flour")
        assert result["quantity"] == 2
        assert result["unit"] == "cup"
        assert result["name"] == "flour"

    def test_fraction(self):
        result = parse_ingredient("1/2 cup sugar")
        assert result["quantity"] == 0.5
        assert result["unit"] == "cup"
        assert result["name"] == "sugar"

    def test_mixed_number(self):
        result = parse_ingredient("2 1/2 cups water")
        assert result["quantity"] == 2.5
        assert result["unit"] == "cup"
        assert result["name"] == "water"

    def test_unicode_fraction(self):
        result = parse_ingredient("\u00BD cup milk")
        assert result["quantity"] == 0.5
        assert result["unit"] == "cup"
        assert result["name"] == "milk"

    def test_range_takes_upper(self):
        result = parse_ingredient("2-3 cloves garlic")
        assert result["quantity"] == 3
        assert result["unit"] == "clove"
        assert result["name"] == "garlic"

    def test_word_number(self):
        result = parse_ingredient("one large onion")
        assert result["quantity"] == 1
        assert result["unit"] is None
        assert "onion" in result["name"]

    def test_word_half(self):
        result = parse_ingredient("half a lemon")
        assert result["quantity"] == 0.5

    def test_no_quantity(self):
        result = parse_ingredient("salt and pepper")
        assert result["quantity"] is None
        assert result["unit"] is None

    def test_strips_leading_dash(self):
        result = parse_ingredient("- 2 cups flour")
        assert result["quantity"] == 2
        assert result["unit"] == "cup"

    def test_unit_normalization(self):
        result = parse_ingredient("3 tablespoons butter")
        assert result["unit"] == "tbsp"

        result = parse_ingredient("2 ounces cheese")
        assert result["unit"] == "oz"

    def test_prep_word_stripping(self):
        result = parse_ingredient("1 cup onion, diced")
        assert "diced" not in result["name"]
        assert result["name"] == "onion"

    def test_display_text_preserves_prep(self):
        result = parse_ingredient("1 cup onion, diced")
        assert "diced" in result["displayText"]

    def test_strips_parentheticals_for_parsing(self):
        result = parse_ingredient("1 can (14 oz) tomatoes")
        assert result["quantity"] == 1
        assert result["unit"] == "can"

    def test_decimal_quantity(self):
        result = parse_ingredient("1.5 lbs chicken")
        assert result["quantity"] == 1.5
        assert result["unit"] == "lb"

    def test_of_after_unit(self):
        result = parse_ingredient("2 cups of rice")
        assert result["name"] == "rice"


class TestIngredientKey:
    def test_with_unit(self):
        parsed = parse_ingredient("2 cups flour")
        assert ingredient_key(parsed) == "cup:flour"

    def test_without_unit(self):
        parsed = parse_ingredient("salt")
        assert ingredient_key(parsed) == "_:salt"


class TestFormatQuantity:
    def test_whole_number(self):
        assert format_quantity(2) == "2"

    def test_half(self):
        assert format_quantity(0.5) == "1/2"

    def test_quarter(self):
        assert format_quantity(0.25) == "1/4"

    def test_mixed_fraction(self):
        assert format_quantity(2.5) == "2 1/2"

    def test_third(self):
        assert format_quantity(1 / 3) == "1/3"

    def test_non_standard_decimal(self):
        result = format_quantity(1.3)
        assert result == "1 1/3"

    def test_plain_decimal(self):
        result = format_quantity(1.43)
        assert result == "1.4"
