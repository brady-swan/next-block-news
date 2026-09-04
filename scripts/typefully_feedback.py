"""Print a bounded, read-only Markdown view of comments on recent Typefully drafts."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nbn import publisher_typefully


def render(rows: list[dict]) -> str:
    lines = ["# Recent Typefully feedback", ""]
    if not rows:
        return "\n".join(lines + ["No matching comment threads."])
    for row in rows:
        title = row.get("title") or "Untitled draft"
        lines.extend([
            f"## Draft {row['draft_id']} — {title}", "",
            f"Created: {row.get('created_at') or 'unknown'}", "",
        ])
        if row.get("draft_text"):
            lines.extend(["Draft text:", "", str(row["draft_text"]), ""])
        for thread in row.get("threads") or []:
            selected = thread.get("selected_text") or "(whole-post comment)"
            lines.extend([f"> Selected: {selected}", ""])
            for comment in thread.get("comments") or []:
                author = comment.get("author") or "Unknown author"
                created = comment.get("created_at") or "unknown time"
                lines.extend([f"- {author} · {created}: {comment.get('text') or ''}", ""])
    return "\n".join(lines).rstrip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read recent Typefully comment threads without modifying them."
    )
    parser.add_argument("--status", choices=("unresolved", "resolved", "all"),
                        default="unresolved")
    parser.add_argument("--drafts", type=int,
                        default=publisher_typefully.FEEDBACK_DRAFT_LIMIT)
    args = parser.parse_args()
    rows = publisher_typefully.collect_recent_feedback(
        status=args.status, draft_limit=args.drafts,
    )
    print(render(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
