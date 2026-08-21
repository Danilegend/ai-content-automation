import sys
from pathlib import Path

import yaml


def approve(path: Path):
    text = path.read_text(encoding="utf-8")

    if not text.startswith("---"):
        raise ValueError("Missing YAML front matter")

    parts = text.split("---", 2)

    if len(parts) != 3:
        raise ValueError("Invalid front matter structure")

    metadata = yaml.safe_load(parts[1])
    body = parts[2]

    if metadata.get("status") != "draft":
        raise ValueError("Only draft content can be approved")

    if metadata.get("approval") != "pending":
        raise ValueError("Content is not pending approval")

    metadata["status"] = "approved"
    metadata["approval"] = "approved"

    new_front_matter = yaml.safe_dump(
        metadata,
        sort_keys=False,
        allow_unicode=True,
    )

    updated = f"---\n{new_front_matter}---{body}"

    path.write_text(updated, encoding="utf-8")


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/approve_content.py <file>")
        sys.exit(1)

    path = Path(sys.argv[1])

    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    approve(path)

    print(f"✅ Content approved: {path}")


if __name__ == "__main__":
    main()
