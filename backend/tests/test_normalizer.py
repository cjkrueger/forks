"""Tests for the ingredient normalizer module."""

from app.normalizer import normalize_ingredient, normalize_ingredients


class TestWordNumbers:
    def test_one(self):
        assert normalize_ingredient("one cup flour") == "1 cup flour"

    def test_two(self):
        assert normalize_ingredient("two eggs") == "2 eggs"

    def test_twelve(self):
        assert normalize_ingredient("twelve tortillas") == "12 tortillas"

    def test_a(self):
        assert normalize_ingredient("a pinch of salt") == "1 pinch of salt"

    def test_an(self):
        assert normalize_ingredient("an avocado") == "1 avocado"

    def test_half(self):
        assert normalize_ingredient("half a cup sugar") == "1/2 cup sugar"

    def test_half_without_article(self):
        assert normalize_ingredient("half cup sugar") == "1/2 cup sugar"

    def test_case_insensitive(self):
        assert normalize_ingredient("One cup flour") == "1 cup flour"
        assert normalize_ingredient("ONE cup flour") == "1 cup flour"

    def test_word_not_in_middle(self):
        """Word numbers in the middle of the string should not be replaced."""
        assert normalize_ingredient("1 cup one-percent milk") == "1 cup one-percent milk"


class TestHyphenatedMixedNumbers:
    def test_basic(self):
        assert normalize_ingredient("1-1/2 cups flour") == "1 1/2 cups flour"

    def test_range_untouched(self):
        assert normalize_ingredient("2-3 cloves garlic") == "2-3 cloves garlic"

    def test_multiple_hyphens(self):
        assert normalize_ingredient("1-1/2 cups chopped 1-1/4 cups diced") == "1 1/2 cups chopped 1 1/4 cups diced"

    def test_larger_fraction(self):
        assert normalize_ingredient("2-3/4 cups milk") == "2 3/4 cups milk"


class TestCompoundContainerAmounts:
    def test_one_15_ounce_can(self):
        assert normalize_ingredient("One 15-ounce can beans") == "1 (15 ounce) can beans"

    def test_one_12_oz_can(self):
        assert normalize_ingredient("one 12 oz can tomatoes") == "1 (12 ounce) can tomatoes"

    def test_two_8_5_ounce_bags(self):
        assert normalize_ingredient("Two 8.5-ounce bags rice") == "2 (8.5 ounce) bags rice"

    def test_a_12_oz_bottle(self):
        assert normalize_ingredient("a 12-oz bottle hot sauce") == "1 (12 ounce) bottle hot sauce"

    def test_an_8_ounce_package(self):
        assert normalize_ingredient("an 8-ounce package cream cheese") == "1 (8 ounce) package cream cheese"

    def test_one_15_ounce_can_with_oz_dot(self):
        assert normalize_ingredient("one 15 oz. can diced tomatoes") == "1 (15 ounce) can diced tomatoes"

    def test_container_jar(self):
        assert normalize_ingredient("one 16-ounce jar salsa") == "1 (16 ounce) jar salsa"

    def test_container_box(self):
        assert normalize_ingredient("one 32-ounce box broth") == "1 (32 ounce) box broth"


class TestNoChange:
    def test_already_numeric(self):
        assert normalize_ingredient("2 cups flour") == "2 cups flour"

    def test_no_amount(self):
        assert normalize_ingredient("Kosher salt and freshly ground black pepper") == "Kosher salt and freshly ground black pepper"

    def test_empty(self):
        assert normalize_ingredient("") == ""

    def test_already_parenthesized(self):
        assert normalize_ingredient("1 (15 ounce) can beans") == "1 (15 ounce) can beans"

    def test_unicode_fraction(self):
        assert normalize_ingredient("½ cup flour") == "½ cup flour"


class TestRealWorldExamples:
    """Test with actual ingredients from recipe files in the repo."""

    def test_7_layer_casserole_bags(self):
        result = normalize_ingredient("Two 8.5-ounce bags microwave white rice")
        assert result == "2 (8.5 ounce) bags microwave white rice"

    def test_7_layer_casserole_can_beans(self):
        result = normalize_ingredient("One 15-ounce can ranch style beans")
        assert result == "1 (15 ounce) can ranch style beans"

    def test_7_layer_casserole_can_tomatoes(self):
        result = normalize_ingredient("One 15-ounce can tomatoes and green chiles")
        assert result == "1 (15 ounce) can tomatoes and green chiles"

    def test_7_layer_casserole_salt_pepper(self):
        """No-amount ingredient should pass through unchanged."""
        result = normalize_ingredient("Kosher salt and freshly ground black pepper")
        assert result == "Kosher salt and freshly ground black pepper"

    def test_pastina_soup_hyphenated(self):
        result = normalize_ingredient("1-1/2 cups chopped onion")
        assert result == "1 1/2 cups chopped onion"

    def test_pastina_soup_parmesan_rind(self):
        """'2-in.' should not be transformed (not a fraction)."""
        result = normalize_ingredient("2-in. Parmesan rind, optional")
        assert result == "2-in. Parmesan rind, optional"

    def test_pastina_fire_roasted_corn(self):
        """Hyphen in 'fire-roasted' should not be affected."""
        result = normalize_ingredient("1 cup frozen fire-roasted corn")
        assert result == "1 cup frozen fire-roasted corn"


class TestBatchNormalize:
    def test_normalize_ingredients_list(self):
        items = [
            "One 15-ounce can beans",
            "1-1/2 cups flour",
            "two eggs",
        ]
        result = normalize_ingredients(items)
        assert result == [
            "1 (15 ounce) can beans",
            "1 1/2 cups flour",
            "2 eggs",
        ]

    def test_empty_list(self):
        assert normalize_ingredients([]) == []
