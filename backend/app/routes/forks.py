import datetime
import logging
from pathlib import Path

import frontmatter
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.generator import slugify
from app.git import git_commit, git_head_hash, git_log, git_rm, git_show
from app.index import RecipeIndex
from app.models import ForkDetail, ForkInput
from app.sections import diff_sections, generate_fork_markdown, merge_content, merge_fork_into_base

logger = logging.getLogger(__name__)


def create_fork_router(index: RecipeIndex, recipes_dir: Path) -> APIRouter:
    router = APIRouter(prefix="/api/recipes/{slug}/forks")

    def _load_base(slug: str):
        """Load the base recipe file; raise 404 if missing."""
        base_path = recipes_dir / f"{slug}.md"
        if not base_path.exists():
            raise HTTPException(status_code=404, detail="Base recipe not found")
        return base_path

    def _fork_path(slug: str, fork_name_slug: str) -> Path:
        return recipes_dir / f"{slug}.fork.{fork_name_slug}.md"

    @router.get("/{fork_name_slug}", response_model=ForkDetail)
    def get_fork(slug: str, fork_name_slug: str):
        path = _fork_path(slug, fork_name_slug)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Fork not found")
        try:
            post = frontmatter.load(path)
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to parse fork file")
        return ForkDetail(
            name=fork_name_slug,
            fork_name=post.metadata.get("fork_name", fork_name_slug),
            author=post.metadata.get("author"),
            date_added=str(post.metadata.get("date_added")) if post.metadata.get("date_added") else None,
            content=post.content,
        )

    @router.post("", status_code=201)
    def create_fork(slug: str, data: ForkInput):
        base_path = _load_base(slug)
        fork_name_slug = slugify(data.fork_name)
        if not fork_name_slug:
            raise HTTPException(status_code=400, detail="Invalid fork name")

        path = _fork_path(slug, fork_name_slug)
        if path.exists():
            raise HTTPException(status_code=409, detail="Fork name already exists")

        base_post = frontmatter.load(base_path)
        changed = diff_sections(
            base_post.content,
            data.ingredients,
            data.instructions,
            data.notes,
        )
        if not changed:
            raise HTTPException(status_code=400, detail="No changes from base recipe")

        head_hash = git_head_hash(recipes_dir)
        md = generate_fork_markdown(
            forked_from=slug,
            fork_name=data.fork_name,
            changed_sections=changed,
            author=data.author,
            forked_at_commit=head_hash if head_hash else None,
        )
        path.write_text(md)
        git_commit(recipes_dir, path, f"Create fork: {data.fork_name} ({slug})")
        index.add_or_update(path)

        return {"name": fork_name_slug, "fork_name": data.fork_name}

    @router.put("/{fork_name_slug}")
    def update_fork(slug: str, fork_name_slug: str, data: ForkInput):
        base_path = _load_base(slug)
        path = _fork_path(slug, fork_name_slug)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Fork not found")

        base_post = frontmatter.load(base_path)
        changed = diff_sections(
            base_post.content,
            data.ingredients,
            data.instructions,
            data.notes,
        )
        if not changed:
            raise HTTPException(status_code=400, detail="No changes from base recipe")

        md = generate_fork_markdown(
            forked_from=slug,
            fork_name=data.fork_name,
            changed_sections=changed,
            author=data.author,
        )
        path.write_text(md)
        git_commit(recipes_dir, path, f"Update fork: {data.fork_name} ({slug})")
        index.add_or_update(path)

        return {"name": fork_name_slug, "fork_name": data.fork_name}

    @router.delete("/{fork_name_slug}", status_code=204)
    def delete_fork(slug: str, fork_name_slug: str):
        path = _fork_path(slug, fork_name_slug)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Fork not found")

        path.unlink()
        git_commit(recipes_dir, path, f"Delete fork: {fork_name_slug} ({slug})")
        index.remove(f"{slug}.fork.{fork_name_slug}")

    @router.get("/{fork_name_slug}/export")
    def export_fork(slug: str, fork_name_slug: str):
        base_path = _load_base(slug)
        fork_path = _fork_path(slug, fork_name_slug)
        if not fork_path.exists():
            raise HTTPException(status_code=404, detail="Fork not found")

        base_post = frontmatter.load(base_path)
        fork_post = frontmatter.load(fork_path)

        # Merge frontmatter: start from base, overlay fork metadata
        merged_meta = dict(base_post.metadata)
        if fork_post.metadata.get("fork_name"):
            merged_meta["title"] = (
                merged_meta.get("title", "") + " (" + fork_post.metadata["fork_name"] + ")"
            )
        if fork_post.metadata.get("author"):
            merged_meta["author"] = fork_post.metadata["author"]
        if fork_post.metadata.get("date_added"):
            merged_meta["date_added"] = fork_post.metadata["date_added"]

        # Build frontmatter block
        fm_lines = ["---"]
        for key, value in merged_meta.items():
            if isinstance(value, list):
                fm_lines.append(f"{key}: [{', '.join(str(v) for v in value)}]")
            else:
                fm_lines.append(f"{key}: {value}")
        fm_lines.append("---")
        fm_block = "\n".join(fm_lines)

        # Merge body content
        merged_body = merge_content(base_post.content, fork_post.content)
        full_markdown = fm_block + "\n" + merged_body

        filename = f"{slug}-{fork_name_slug}.md"
        return PlainTextResponse(
            content=full_markdown,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @router.get("/{fork_name_slug}/history")
    def fork_history(slug: str, fork_name_slug: str, content: bool = False):
        """Return git history for a fork file."""
        path = _fork_path(slug, fork_name_slug)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Fork not found")

        entries = git_log(recipes_dir, path)
        if content:
            for entry in entries:
                entry["content"] = git_show(recipes_dir, entry["hash"], path)
        return {"history": entries}

    @router.post("/{fork_name_slug}/merge")
    def merge_fork(slug: str, fork_name_slug: str):
        """Merge a fork's changes back into the base recipe."""
        base_path = _load_base(slug)
        fork_path = _fork_path(slug, fork_name_slug)
        if not fork_path.exists():
            raise HTTPException(status_code=404, detail="Fork not found")

        base_post = frontmatter.load(base_path)
        fork_post = frontmatter.load(fork_path)

        # Merge fork content into base body
        merged_body = merge_fork_into_base(base_post.content, fork_post.content)
        base_post.content = merged_body

        # Write updated base file
        base_path.write_text(frontmatter.dumps(base_post))
        fork_name = fork_post.metadata.get("fork_name", fork_name_slug)
        git_commit(recipes_dir, base_path, f"Merge fork '{fork_name}' into {slug}")

        # Mark fork as merged
        fork_post.metadata["merged_at"] = datetime.date.today().isoformat()
        fork_path.write_text(frontmatter.dumps(fork_post))
        git_commit(recipes_dir, fork_path, f"Mark fork '{fork_name}' as merged ({slug})")

        # Re-index both files
        index.add_or_update(base_path)
        index.add_or_update(fork_path)

        return {"merged": True, "fork_name": fork_name_slug}

    return router
