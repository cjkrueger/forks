"""Tests for meal planner API routes."""
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def tmp_recipes(tmp_path):
    recipe = tmp_path / "birria-tacos.md"
    recipe.write_text(
        "---\ntitle: Birria Tacos\ntags: [mexican]\nservings: 6\n---\n\n"
        "# Birria Tacos\n\n## Ingredients\n\n- 2 lbs beef\n\n"
        "## Instructions\n\n1. Cook beef\n"
    )
    recipe2 = tmp_path / "chicken-soup.md"
    recipe2.write_text(
        "---\ntitle: Chicken Soup\ntags: [soup]\nservings: 8\n---\n\n"
        "# Chicken Soup\n\n## Ingredients\n\n- 1 chicken\n\n"
        "## Instructions\n\n1. Boil chicken\n"
    )
    return tmp_path


@pytest.fixture
def client(tmp_recipes):
    with patch("app.routes.planner.git_commit"):
        app = create_app(recipes_dir=tmp_recipes)
        yield TestClient(app)


class TestGetMealPlan:
    def test_empty_plan(self, client):
        resp = client.get("/api/meal-plan?week=2026-W07")
        assert resp.status_code == 200
        data = resp.json()["weeks"]
        # Returns 7 days for the requested week, all empty
        assert len(data) == 7
        assert all(v == [] for v in data.values())

    def test_get_with_week_filter(self, client, tmp_recipes):
        client.put("/api/meal-plan", json={
            "weeks": {
                "2026-02-09": [{"slug": "birria-tacos"}],
                "2026-02-10": [{"slug": "chicken-soup"}],
                "2026-02-20": [{"slug": "birria-tacos"}],
            }
        })
        resp = client.get("/api/meal-plan?week=2026-W07")
        assert resp.status_code == 200
        data = resp.json()["weeks"]
        assert "2026-02-09" in data
        assert "2026-02-10" in data
        assert "2026-02-20" not in data

    def test_get_week_fills_empty_days(self, client, tmp_recipes):
        client.put("/api/meal-plan", json={
            "weeks": {
                "2026-02-09": [{"slug": "birria-tacos"}],
            }
        })
        resp = client.get("/api/meal-plan?week=2026-W07")
        data = resp.json()["weeks"]
        assert len(data) == 7
        assert data["2026-02-09"] == [{"slug": "birria-tacos"}]
        assert data["2026-02-11"] == []


class TestSaveMealPlan:
    def test_save_and_retrieve(self, client):
        resp = client.put("/api/meal-plan", json={
            "weeks": {
                "2026-02-09": [{"slug": "birria-tacos"}],
                "2026-02-10": [{"slug": "chicken-soup", "fork": "vegan"}],
            }
        })
        assert resp.status_code == 200
        data = resp.json()["weeks"]
        assert len(data["2026-02-09"]) == 1
        assert data["2026-02-09"][0]["slug"] == "birria-tacos"
        assert data["2026-02-10"][0]["fork"] == "vegan"

    def test_merge_preserves_other_days(self, client):
        client.put("/api/meal-plan", json={
            "weeks": {"2026-02-09": [{"slug": "birria-tacos"}]}
        })
        client.put("/api/meal-plan", json={
            "weeks": {"2026-02-10": [{"slug": "chicken-soup"}]}
        })
        resp = client.get("/api/meal-plan?week=2026-W07")
        data = resp.json()["weeks"]
        assert "2026-02-09" in data
        assert "2026-02-10" in data

    def test_empty_day_removes_it(self, client):
        client.put("/api/meal-plan", json={
            "weeks": {"2026-02-09": [{"slug": "birria-tacos"}]}
        })
        client.put("/api/meal-plan", json={
            "weeks": {"2026-02-09": []}
        })
        resp = client.get("/api/meal-plan?week=2026-W07")
        data = resp.json()["weeks"]
        # Day is present but empty (GET fills all 7 days)
        assert data["2026-02-09"] == []

    def test_multiple_meals_per_day(self, client):
        resp = client.put("/api/meal-plan", json={
            "weeks": {
                "2026-02-09": [
                    {"slug": "birria-tacos"},
                    {"slug": "chicken-soup"},
                ]
            }
        })
        assert resp.status_code == 200
        assert len(resp.json()["weeks"]["2026-02-09"]) == 2

    def test_writes_per_week_file(self, client, tmp_recipes):
        client.put("/api/meal-plan", json={
            "weeks": {"2026-02-09": [{"slug": "birria-tacos"}]}
        })
        plan_file = tmp_recipes / "meal-plans" / "2026-W07.md"
        assert plan_file.exists()
        content = plan_file.read_text()
        assert "birria-tacos" in content

    def test_cross_week_save(self, client, tmp_recipes):
        """Saving dates across two weeks creates two separate files."""
        client.put("/api/meal-plan", json={
            "weeks": {
                "2026-02-09": [{"slug": "birria-tacos"}],   # W07
                "2026-02-16": [{"slug": "chicken-soup"}],   # W08
            }
        })
        assert (tmp_recipes / "meal-plans" / "2026-W07.md").exists()
        assert (tmp_recipes / "meal-plans" / "2026-W08.md").exists()


class TestAddMealToDay:
    def test_add_meal(self, client):
        resp = client.post("/api/meal-plan/2026-02-09", json={"slug": "birria-tacos"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["date"] == "2026-02-09"
        assert len(data["meals"]) == 1
        assert data["meals"][0]["slug"] == "birria-tacos"

    def test_add_meal_with_fork(self, client):
        resp = client.post("/api/meal-plan/2026-02-09", json={
            "slug": "birria-tacos", "fork": "spicy"
        })
        assert resp.json()["meals"][0]["fork"] == "spicy"

    def test_add_multiple_meals(self, client):
        client.post("/api/meal-plan/2026-02-09", json={"slug": "birria-tacos"})
        resp = client.post("/api/meal-plan/2026-02-09", json={"slug": "chicken-soup"})
        assert len(resp.json()["meals"]) == 2

    def test_add_creates_week_file(self, client, tmp_recipes):
        client.post("/api/meal-plan/2026-02-09", json={"slug": "birria-tacos"})
        assert (tmp_recipes / "meal-plans" / "2026-W07.md").exists()

    def test_invalid_date(self, client):
        resp = client.post("/api/meal-plan/not-a-date", json={"slug": "birria-tacos"})
        assert resp.status_code == 400


class TestRemoveMealFromDay:
    def test_remove_meal(self, client):
        client.post("/api/meal-plan/2026-02-09", json={"slug": "birria-tacos"})
        client.post("/api/meal-plan/2026-02-09", json={"slug": "chicken-soup"})
        resp = client.delete("/api/meal-plan/2026-02-09/0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["meals"]) == 1
        assert data["meals"][0]["slug"] == "chicken-soup"

    def test_remove_out_of_range(self, client):
        client.post("/api/meal-plan/2026-02-09", json={"slug": "birria-tacos"})
        resp = client.delete("/api/meal-plan/2026-02-09/5")
        assert resp.status_code == 404

    def test_remove_last_meal(self, client, tmp_recipes):
        client.post("/api/meal-plan/2026-02-09", json={"slug": "birria-tacos"})
        resp = client.delete("/api/meal-plan/2026-02-09/0")
        assert resp.json()["meals"] == []
        # Week file should be deleted when empty
        assert not (tmp_recipes / "meal-plans" / "2026-W07.md").exists()


class TestClearDay:
    def test_clear_day(self, client):
        client.post("/api/meal-plan/2026-02-09", json={"slug": "birria-tacos"})
        client.post("/api/meal-plan/2026-02-09", json={"slug": "chicken-soup"})
        resp = client.delete("/api/meal-plan/2026-02-09")
        assert resp.status_code == 200
        assert resp.json()["meals"] == []

    def test_clear_empty_day(self, client):
        resp = client.delete("/api/meal-plan/2026-02-09")
        assert resp.status_code == 200
        assert resp.json()["meals"] == []
