"""Tests for recipe stream/timeline endpoint."""
import textwrap
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

BASE_RECIPE = textwrap.dedent("""\
    ---
    title: Pasta Carbonara
    tags: [italian]
    date_added: 2026-02-01
    changelog:
      - date: "2026-02-01"
        action: created
        summary: "Created Pasta Carbonara"
      - date: "2026-02-03"
        action: edited
        summary: "Updated ingredients list"
    ---

    # Pasta Carbonara

    ## Ingredients

    - 400g spaghetti
    - 200g guanciale
    - 4 egg yolks
    - 100g pecorino

    ## Instructions

    1. Cook pasta
    2. Fry guanciale
    3. Mix eggs and cheese
    4. Combine
""")

RECIPE_NO_CHANGELOG = textwrap.dedent("""\
    ---
    title: Simple Salad
    tags: [salad]
    ---

    # Simple Salad

    ## Ingredients

    - Lettuce
    - Tomato
""")


@pytest.fixture
def tmp_recipes(tmp_path):
    recipe = tmp_path / "pasta-carbonara.md"
    recipe.write_text(BASE_RECIPE)
    return tmp_path


@pytest.fixture
def client(tmp_recipes):
    app = create_app(recipes_dir=tmp_recipes)
    return TestClient(app)


class TestStreamEndpoint:
    def test_returns_stream_for_recipe(self, client):
        resp = client.get("/api/recipes/pasta-carbonara/stream")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert isinstance(data["events"], list)

    def test_404_for_missing_recipe(self, client):
        resp = client.get("/api/recipes/nonexistent/stream")
        assert resp.status_code == 404

    def test_includes_changelog_events(self, client):
        resp = client.get("/api/recipes/pasta-carbonara/stream")
        events = resp.json()["events"]
        types = [e["type"] for e in events]
        assert "created" in types
        assert "edited" in types
        assert len(events) == 2

    def test_events_sorted_chronologically(self, client):
        resp = client.get("/api/recipes/pasta-carbonara/stream")
        events = resp.json()["events"]
        dates = [e["date"] for e in events]
        assert dates == sorted(dates)

    def test_created_event_details(self, client):
        resp = client.get("/api/recipes/pasta-carbonara/stream")
        events = resp.json()["events"]
        created = [e for e in events if e["type"] == "created"]
        assert len(created) == 1
        assert created[0]["date"] == "2026-02-01"
        assert created[0]["message"] == "Created Pasta Carbonara"

    def test_edited_event_details(self, client):
        resp = client.get("/api/recipes/pasta-carbonara/stream")
        events = resp.json()["events"]
        edited = [e for e in events if e["type"] == "edited"]
        assert len(edited) == 1
        assert edited[0]["date"] == "2026-02-03"
        assert edited[0]["message"] == "Updated ingredients list"

    def test_empty_changelog(self, tmp_path):
        recipe = tmp_path / "simple-salad.md"
        recipe.write_text(RECIPE_NO_CHANGELOG)
        app = create_app(recipes_dir=tmp_path)
        c = TestClient(app)
        resp = c.get("/api/recipes/simple-salad/stream")
        assert resp.status_code == 200
        events = resp.json()["events"]
        assert events == []

    def test_includes_fork_events(self, tmp_recipes):
        fork = tmp_recipes / "pasta-carbonara.fork.moms-version.md"
        fork.write_text(textwrap.dedent("""\
            ---
            forked_from: pasta-carbonara
            fork_name: Mom's Version
            author: mom
            date_added: 2026-02-05
            changelog:
              - date: "2026-02-05"
                action: created
                summary: "Forked: Mom's Version"
              - date: "2026-02-06"
                action: edited
                summary: "Swapped spaghetti for rigatoni"
            ---

            ## Ingredients

            - 400g rigatoni
        """))
        app = create_app(recipes_dir=tmp_recipes)
        c = TestClient(app)
        resp = c.get("/api/recipes/pasta-carbonara/stream")
        events = resp.json()["events"]

        # Fork "created" action should be mapped to "forked" event type
        fork_events = [e for e in events if e["type"] == "forked"]
        assert len(fork_events) == 1
        assert fork_events[0]["fork_name"] == "Mom's Version"
        assert fork_events[0]["fork_slug"] == "moms-version"
        assert fork_events[0]["date"] == "2026-02-05"

        # Fork edit events should retain "edited" type and include fork info
        fork_edits = [e for e in events if e["type"] == "edited" and e["fork_name"] is not None]
        assert len(fork_edits) == 1
        assert fork_edits[0]["fork_name"] == "Mom's Version"
        assert fork_edits[0]["fork_slug"] == "moms-version"
        assert fork_edits[0]["message"] == "Swapped spaghetti for rigatoni"

    def test_includes_merged_events(self, tmp_recipes):
        fork = tmp_recipes / "pasta-carbonara.fork.moms-version.md"
        fork.write_text(textwrap.dedent("""\
            ---
            forked_from: pasta-carbonara
            fork_name: Mom's Version
            author: mom
            date_added: 2026-02-05
            merged_at: 2026-02-08
            changelog:
              - date: "2026-02-05"
                action: created
                summary: "Forked: Mom's Version"
              - date: "2026-02-08"
                action: merged
                summary: "Merged Mom's Version into base recipe"
            ---

            ## Ingredients

            - 400g rigatoni
        """))
        app = create_app(recipes_dir=tmp_recipes)
        c = TestClient(app)
        resp = c.get("/api/recipes/pasta-carbonara/stream")
        events = resp.json()["events"]
        merged_events = [e for e in events if e["type"] == "merged"]
        assert len(merged_events) == 1
        assert merged_events[0]["fork_name"] == "Mom's Version"
        assert merged_events[0]["date"] == "2026-02-08"

    def test_mixed_events_sorted(self, tmp_recipes):
        fork = tmp_recipes / "pasta-carbonara.fork.dads-twist.md"
        fork.write_text(textwrap.dedent("""\
            ---
            forked_from: pasta-carbonara
            fork_name: Dad's Twist
            author: dad
            date_added: 2026-02-02
            changelog:
              - date: "2026-02-02"
                action: created
                summary: "Forked: Dad's Twist"
            ---

            ## Ingredients

            - 400g penne
        """))
        app = create_app(recipes_dir=tmp_recipes)
        c = TestClient(app)
        resp = c.get("/api/recipes/pasta-carbonara/stream")
        events = resp.json()["events"]

        # Base recipe has events on 2026-02-01 and 2026-02-03
        # Fork has event on 2026-02-02
        # They should be interleaved in date order
        dates = [e["date"] for e in events]
        assert dates == sorted(dates)
        assert len(events) == 3
        assert events[0]["type"] == "created"       # 2026-02-01 base
        assert events[1]["type"] == "forked"         # 2026-02-02 fork
        assert events[2]["type"] == "edited"         # 2026-02-03 base edit

    def test_no_commit_field_in_events(self, client):
        """Events from changelogs should not have commit hashes."""
        resp = client.get("/api/recipes/pasta-carbonara/stream")
        events = resp.json()["events"]
        for event in events:
            assert event["commit"] is None
