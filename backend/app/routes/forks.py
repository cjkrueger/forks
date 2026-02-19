import datetime
import logging
from pathlib import Path

import frontmatter
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.changelog import append_changelog_entry, remove_changelog_entries_for_fork
from app.generator import slugify
from app.git import git_commit, git_find_commit, git_head_hash, git_log, git_rm, git_show
from app.index import RecipeIndex
from pydantic import BaseModel

from app.models import ForkDetail, ForkInput
from app.sections import (
    detect_changed_sections,
    diff_sections,
    generate_fork_markdown,
    merge_content,
    merge_fork_into_base,
)
from app.validation import validate_slug

logger = logging.getLogger(__name__)


class MergeForkRequest(BaseModel):
    note: str


class FailForkRequest(BaseModel):
    reason: str


def create_fork_router(index: RecipeIndex, recipes_dir: Path) -> APIRouter:
    router = APIRouter(prefix="/api/recipes/{slug}/forks")

    def _load_base(slug: str):
        """Load the base recipe file; raise 404 if missing."""
        validate_slug(slug)
        base_path = recipes_dir / f"{slug}.md"
        if not base_path.exists():
            raise HTTPException(status_code=404, detail="Base recipe not found")
        return base_path

    def _fork_path(slug: str, fork_name_slug: str) -> Path:
        validate_slug(fork_name_slug)
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

        # Append changelog entry and set initial version
        fork_post = frontmatter.load(path)
        append_changelog_entry(fork_post, "created", "Forked from original")
        fork_post.metadata["version"] = 1
        path.write_text(frontmatter.dumps(fork_post))

        git_commit(recipes_dir, path, f"Create fork: {data.fork_name} ({slug})")
        index.add_or_update(path)

        return {"name": fork_name_slug, "fork_name": data.fork_name}

    @router.put("/{fork_name_slug}")
    def update_fork(slug: str, fork_name_slug: str, data: ForkInput):
        base_path = _load_base(slug)
        path = _fork_path(slug, fork_name_slug)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Fork not found")

        # Read old fork content and changelog before overwriting
        old_fork_post = frontmatter.load(path)
        old_fork_content = old_fork_post.content
        old_changelog = old_fork_post.metadata.get("changelog", [])

        # Optimistic locking: reject stale writes
        old_version = int(old_fork_post.metadata.get("version", 0))
        if data.version is not None and data.version != old_version:
            raise HTTPException(
                status_code=409,
                detail="Fork was modified by another user. Please reload and try again.",
            )

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

        # Detect changed sections between old and new fork content
        new_fork_post = frontmatter.load(path)
        section_changes = detect_changed_sections(old_fork_content, new_fork_post.content)
        if section_changes:
            summary = "Edited " + ", ".join(section_changes)
        else:
            summary = "Edited metadata"
        new_fork_post.metadata["changelog"] = old_changelog
        append_changelog_entry(new_fork_post, "edited", summary)
        new_fork_post.metadata["version"] = old_version + 1
        path.write_text(frontmatter.dumps(new_fork_post))

        git_commit(recipes_dir, path, f"Update fork: {data.fork_name} ({slug})")
        index.add_or_update(path)

        return {"name": fork_name_slug, "fork_name": data.fork_name}

    @router.delete("/{fork_name_slug}", status_code=204)
    def delete_fork(slug: str, fork_name_slug: str):
        path = _fork_path(slug, fork_name_slug)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Fork not found")

        # Load fork to get display name before deleting
        fork_post = frontmatter.load(path)
        fork_name = fork_post.metadata.get("fork_name", fork_name_slug)

        # Clean base recipe changelog
        base_path = _load_base(slug)
        base_post = frontmatter.load(base_path)
        remove_changelog_entries_for_fork(base_post, fork_name)
        base_path.write_text(frontmatter.dumps(base_post))

        # Delete fork file
        path.unlink()

        # Commit both changes together
        git_commit(recipes_dir, [base_path, path], f"Delete fork: {fork_name_slug} ({slug})")
        index.add_or_update(base_path)
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
    def merge_fork(slug: str, fork_name_slug: str, data: MergeForkRequest):
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

        fork_name = fork_post.metadata.get("fork_name", fork_name_slug)

        # Append changelog to base recipe
        append_changelog_entry(base_post, "merged", f"Merged fork '{fork_name}': {data.note}")

        # Write updated base file
        base_path.write_text(frontmatter.dumps(base_post))
        git_commit(recipes_dir, base_path, f"Merge fork '{fork_name}' into {slug}")

        # Mark fork as merged and append changelog
        fork_post.metadata["merged_at"] = datetime.date.today().isoformat()
        append_changelog_entry(fork_post, "merged", f"Merged into {slug}")
        fork_path.write_text(frontmatter.dumps(fork_post))
        git_commit(recipes_dir, fork_path, f"Mark fork '{fork_name}' as merged ({slug})")

        # Re-index both files
        index.add_or_update(base_path)
        index.add_or_update(fork_path)

        return {"merged": True, "fork_name": fork_name_slug}

    @router.post("/{fork_name_slug}/unmerge")
    def unmerge_fork(slug: str, fork_name_slug: str):
        """Undo a previous merge by restoring the base recipe from git history."""
        base_path = _load_base(slug)
        fork_path = _fork_path(slug, fork_name_slug)
        if not fork_path.exists():
            raise HTTPException(status_code=404, detail="Fork not found")

        fork_post = frontmatter.load(fork_path)
        if not fork_post.metadata.get("merged_at"):
            raise HTTPException(status_code=400, detail="Fork is not merged")

        fork_name = fork_post.metadata.get("fork_name", fork_name_slug)

        # Find the merge commit for the base recipe
        merge_commit = git_find_commit(
            recipes_dir, base_path, f"Merge fork '{fork_name}' into {slug}"
        )
        if not merge_commit:
            raise HTTPException(
                status_code=409,
                detail="Merge commit not found in history",
            )

        # Restore base content from the parent of the merge commit
        pre_merge_content = git_show(recipes_dir, f"{merge_commit}~1", base_path)
        if not pre_merge_content:
            raise HTTPException(
                status_code=409,
                detail="Could not retrieve pre-merge content",
            )

        # Parse the restored content and write it back
        base_post = frontmatter.loads(pre_merge_content)
        append_changelog_entry(base_post, "unmerged", f"Unmerged fork '{fork_name}'")
        base_path.write_text(frontmatter.dumps(base_post))

        # Clear merged_at on the fork
        del fork_post.metadata["merged_at"]
        append_changelog_entry(fork_post, "unmerged", f"Unmerged from {slug}")
        fork_path.write_text(frontmatter.dumps(fork_post))

        # Commit and re-index both files
        git_commit(
            recipes_dir,
            [base_path, fork_path],
            f"Unmerge fork '{fork_name}' from {slug}",
        )
        index.add_or_update(base_path)
        index.add_or_update(fork_path)

        return {"unmerged": True, "fork_name": fork_name_slug}

    @router.post("/{fork_name_slug}/fail")
    def fail_fork(slug: str, fork_name_slug: str, data: FailForkRequest):
        """Mark a fork as failed with a reason."""
        fork_path = _fork_path(slug, fork_name_slug)
        if not fork_path.exists():
            raise HTTPException(status_code=404, detail="Fork not found")

        fork_post = frontmatter.load(fork_path)
        if fork_post.metadata.get("failed_at"):
            raise HTTPException(status_code=400, detail="Fork is already marked as failed")

        fork_name = fork_post.metadata.get("fork_name", fork_name_slug)

        fork_post.metadata["failed_at"] = datetime.date.today().isoformat()
        fork_post.metadata["failed_reason"] = data.reason
        append_changelog_entry(fork_post, "failed", f"Marked as failed: {data.reason}")
        fork_path.write_text(frontmatter.dumps(fork_post))

        git_commit(recipes_dir, fork_path, f"Mark fork '{fork_name}' as failed ({slug})")
        index.add_or_update(fork_path)

        return {"failed": True, "fork_name": fork_name_slug}

    @router.post("/{fork_name_slug}/unfail")
    def unfail_fork(slug: str, fork_name_slug: str):
        """Reactivate a previously failed fork."""
        fork_path = _fork_path(slug, fork_name_slug)
        if not fork_path.exists():
            raise HTTPException(status_code=404, detail="Fork not found")

        fork_post = frontmatter.load(fork_path)
        if not fork_post.metadata.get("failed_at"):
            raise HTTPException(status_code=400, detail="Fork is not failed")

        fork_name = fork_post.metadata.get("fork_name", fork_name_slug)

        del fork_post.metadata["failed_at"]
        if "failed_reason" in fork_post.metadata:
            del fork_post.metadata["failed_reason"]
        append_changelog_entry(fork_post, "unfailed", f"Reactivated fork '{fork_name}'")
        fork_path.write_text(frontmatter.dumps(fork_post))

        git_commit(recipes_dir, fork_path, f"Reactivate fork '{fork_name}' ({slug})")
        index.add_or_update(fork_path)

        return {"unfailed": True, "fork_name": fork_name_slug}

    return router
