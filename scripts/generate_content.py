import os
import re
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv
from google import genai

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
TOPICS_FILE = BASE_DIR / "config" / "topics.yaml"
OUTPUT_DIR = BASE_DIR / "content" / "drafts"

MODEL = "gemini-3.6-flash"


def load_topics():
    with TOPICS_FILE.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)["topics"]


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def generate_post(topic, category):
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are an experienced IT professional and technical content creator.

Create one high-quality social media post about:

Topic: {topic}
Category: {category}

Audience:
- IT support technicians
- system administrators
- developers
- networking professionals
- people learning IT

Requirements:
- Be technically useful and accurate.
- Use a professional but approachable tone.
- Start with a strong hook.
- Give practical information rather than generic motivation.
- Include one useful example, command, technique, or real-world scenario when appropriate.
- End with a short question that encourages discussion.
- Include 3 to 5 relevant hashtags.
- Do not invent statistics or claims.
- Do not mention that you are an AI.
- Keep the post suitable for LinkedIn.
- Aim for approximately 150–250 words.

Return only the post text.
"""

    import time

    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
            )

            if not response.text:
                raise RuntimeError("Gemini returned an empty response")

            return response.text.strip()

        except Exception as exc:
            if attempt == max_attempts:
                raise

            delay = attempt * 5
            print(
                f"Gemini request failed (attempt {attempt}/{max_attempts}). "
                f"Retrying in {delay} seconds..."
            )
            print(f"Reason: {exc}")
            time.sleep(delay)


def save_post(topic, category, post):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(topic)

    output_file = OUTPUT_DIR / f"{today}-{slug}.md"

    content = f"""---
title: "AI-generated post about {topic}"
topic: "{topic}"
category: "{category}"
status: "draft"
publish: false
platforms:
  - linkedin
tags:
  - "{slug}"
  - "IT"
  - "Technology"
created_at: "{today}"
---

{post}
"""

    output_file.write_text(content, encoding="utf-8")

    return output_file


def select_topic(topics):
    """Select a topic deterministically based on the current date."""
    today = datetime.now().date()
    index = today.toordinal() % len(topics)
    return topics[index]


def main():
    topics = load_topics()

    topic = select_topic(topics)

    print(
        f"Selected topic: {topic['name']} "
        f"({topic['category']})"
    )

    today = datetime.now().strftime("%Y-%m-%d")
    expected_file = OUTPUT_DIR / f"{today}-{slugify(topic['name'])}.md"

    if expected_file.exists():
        print(f"Content already exists: {expected_file}")
        print("Skipping generation to avoid a duplicate.")
        return

    post = generate_post(
        topic["name"],
        topic["category"],
    )

    output_file = save_post(
        topic["name"],
        topic["category"],
        post,
    )

    print(f"Content generated: {output_file}")


if __name__ == "__main__":
    main()
