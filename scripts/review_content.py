import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv
from google import genai

# Ensure project root is in sys.path to import utils cleanly
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.utils import retry_with_backoff

CONFIG_FILE = BASE_DIR / "config" / "content_quality.yaml"


def load_quality_config():
    with CONFIG_FILE.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


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


# Retry helper wrapped around Gemini API call
@retry_with_backoff(retries=4, backoff_in_seconds=5)
def call_gemini_api(client, model, prompt):
    """Executes Gemini API calls with automatic exponential backoff retries."""
    return client.models.generate_content(
        model=model,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
        },
    )


def review_post(body: str, config: dict):
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    client = genai.Client(api_key=api_key)

    criteria = config["criteria"]
    minimum_score = config["minimum_score"]

    criteria_text = "\n".join(
        f"- {name} (weight {item['weight']}): "
        f"{item['description']}"
        for name, item in criteria.items()
    )

    prompt = f"""
You are a strict technical content reviewer.

Review the following LinkedIn post.

CONTENT:
{body}

QUALITY CRITERIA:
{criteria_text}

Minimum passing score: {minimum_score}/10.

For every criterion, give a score from 0 to 10.

Calculate an overall weighted score from 0 to 10.

Be especially strict about technical accuracy.
Do not reward content simply because it sounds professional.

Return ONLY valid JSON in this exact structure:

{{
  "overall_score": 0,
  "passed": false,
  "criteria": {{
    "hook": {{
      "score": 0,
      "reason": ""
    }},
    "usefulness": {{
      "score": 0,
      "reason": ""
    }},
    "technical_accuracy": {{
      "score": 0,
      "reason": ""
    }},
    "readability": {{
      "score": 0,
      "reason": ""
    }},
    "engagement": {{
      "score": 0,
      "reason": ""
    }},
    "originality": {{
      "score": 0,
      "reason": ""
    }},
    "linkedin_format": {{
      "score": 0,
      "reason": ""
    }}
  }},
  "summary": ""
}}
"""

    # Model call wrapped with retry backoff function
    response = call_gemini_api(
        client=client,
        model="gemini-2.5-flash",
        prompt=prompt,
    )

    result = json.loads(response.text)

    result["passed"] = (
        float(result["overall_score"]) >= minimum_score
    )

    return result


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python -m scripts.review_content <file>"
        )
        sys.exit(1)

    path = Path(sys.argv[1])

    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    metadata, body = load_post(path)
    config = load_quality_config()

    print(f"Reviewing: {path.name}")

    result = review_post(body, config)

    metadata["review"] = {
        "overall_score": result["overall_score"],
        "passed": result["passed"],
        "criteria": result["criteria"],
        "summary": result["summary"],
        "reviewed_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    save_post(path, metadata, body)

    print("\n" + "=" * 60)
    print("CONTENT QUALITY REVIEW")
    print("=" * 60)

    print(
        f"\nOverall score: "
        f"{result['overall_score']}/10"
    )

    print(
        f"Passed: "
        f"{'YES' if result['passed'] else 'NO'}"
    )

    for name, item in result["criteria"].items():
        print(
            f"\n{name}: "
            f"{item['score']}/10"
        )
        print(f"  {item['reason']}")

    print("\nSummary:")
    print(result["summary"])

    print("\n✅ Review saved to content metadata.")

    print("=" * 60)


if __name__ == "__main__":
    main()