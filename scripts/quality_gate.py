import sys
from pathlib import Path

import yaml


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

    path.write_text(
        f"---\n{front_matter}---\n\n{body}\n",
        encoding="utf-8",
    )


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python -m scripts.quality_gate <file>"
        )
        sys.exit(1)

    path = Path(sys.argv[1])

    if not path.exists():
        raise FileNotFoundError(path)

    metadata, body = load_post(path)

    review = metadata.get("review")

    if not review:
        raise RuntimeError(
            "No quality review found. "
            "Run review_content first."
        )

    score = float(review.get("overall_score", 0))
    passed = review.get("passed", False)

    print(f"Quality score: {score}/10")
    print(f"Reviewer passed: {passed}")

    if passed:
        metadata["status"] = "approved"
        metadata["approval"] = "approved"

        print("✅ QUALITY GATE PASSED")
        print("Content approved for publishing.")

    else:
        metadata["status"] = "rejected"
        metadata["approval"] = "rejected"
        metadata["publish"] = False

        print("❌ QUALITY GATE FAILED")
        print("Content will NOT be published.")

    save_post(path, metadata, body)


if __name__ == "__main__":
    main()
