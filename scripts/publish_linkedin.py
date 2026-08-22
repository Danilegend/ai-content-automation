import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from publishers.linkedin import LinkedInPublisher


def load_post(path: Path):
    text = path.read_text(encoding="utf-8")

    if not text.startswith("---"):
        raise ValueError("Missing YAML front matter")

    parts = text.split("---", 2)

    if len(parts) != 3:
        raise ValueError("Invalid front matter structure")

    metadata = yaml.safe_load(parts[1])
    body = parts[2].strip()

    return metadata, body


def save_post(path: Path, metadata: dict, body: str):
    front_matter = yaml.safe_dump(
        metadata,
        sort_keys=False,
        allow_unicode=True,
    )

    content = f"---\n{front_matter}---\n\n{body}\n"

    path.write_text(content, encoding="utf-8")


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.publish_linkedin <file>")
        sys.exit(1)

    path = Path(sys.argv[1])

    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    metadata, body = load_post(path)

    print(f"Content: {path.name}")
    print(f"Status: {metadata.get('status')}")
    print(f"Approval: {metadata.get('approval')}")
    print(f"Publish: {metadata.get('publish')}")

    # Duplicate protection
    linkedin = metadata.get("linkedin", {})

    if linkedin.get("status") == "published":
        print("⏭️ Already published to LinkedIn.")
        print(f"Post ID: {linkedin.get('post_id')}")
        return

    if metadata.get("status") != "approved":
        raise RuntimeError("Content is not approved")

    if metadata.get("approval") != "approved":
        raise RuntimeError("Approval state is not approved")

    if metadata.get("publish") is not True:
        raise RuntimeError(
            "Publishing disabled. Set publish: true to publish."
        )

    publisher = LinkedInPublisher(dry_run=False)

    post_id = publisher.publish(body)

    metadata["linkedin"] = {
        "status": "published",
        "post_id": post_id,
        "published_at": datetime.now(timezone.utc).isoformat(),
    }

    save_post(path, metadata, body)

    print(f"✅ LinkedIn post published: {post_id}")
    print("✅ Publishing metadata saved.")


if __name__ == "__main__":
    main()
