import re
import sys
from pathlib import Path

import yaml


REQUIRED_FIELDS = [
    "title",
    "topic",
    "category",
    "status",
    "approval",
    "publish",
    "platforms",
    "tags",
    "created_at",
]


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


def validate(path: Path):
    errors = []

    metadata, body = load_post(path)

    for field in REQUIRED_FIELDS:
        if field not in metadata:
            errors.append(f"Missing required field: {field}")

    if not body:
        errors.append("Post body is empty")

    word_count = len(body.split())

    if word_count < 50:
        errors.append(f"Post is too short: {word_count} words")

    if word_count > 350:
        errors.append(f"Post is too long: {word_count} words")

    if not re.search(r"#\w+", body):
        errors.append("No hashtags found")

    if metadata.get("status") != "draft":
        errors.append("New content must have status: draft")

    if metadata.get("approval") != "pending":
        errors.append("New content must have approval: pending")

    if metadata.get("publish") is not False:
        errors.append("New content must have publish: false")

    if not isinstance(metadata.get("platforms"), list):
        errors.append("Platforms must be a list")

    if not isinstance(metadata.get("tags"), list):
        errors.append("Tags must be a list")

    return errors


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate_content.py <file>")
        sys.exit(1)

    path = Path(sys.argv[1])

    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    errors = validate(path)

    if errors:
        print("❌ Validation failed:")

        for error in errors:
            print(f" - {error}")

        sys.exit(1)

    print(f"✅ Validation passed: {path}")


if __name__ == "__main__":
    main()
