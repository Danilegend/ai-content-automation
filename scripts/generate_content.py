#!/usr/bin/env python3
import argparse
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml
from google import genai
from google.genai import errors

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Model configurations - Use current active models
MODEL = "gemini-3.6-flash"
FALLBACK_MODEL = "gemini-2.0-flash"  # or gemini-1.5-flash


def get_recent_topics(days=10):
    """Scans existing published posts and drafts to extract recently used topics."""
    published_dir = BASE_DIR / "content" / "published"
    drafts_dir = BASE_DIR / "content" / "drafts"

    recent_topics = set()
    all_files = []

    if published_dir.exists():
        all_files.extend(list(published_dir.glob("*.md")))
    if drafts_dir.exists():
        all_files.extend(list(drafts_dir.glob("*.md")))

    # Sort files by modification time (most recent first)
    all_files = sorted(all_files, key=lambda p: p.stat().st_mtime, reverse=True)[:days]

    for file_path in all_files:
        try:
            content = file_path.read_text(encoding="utf-8")
            if content.startswith("---"):
                parts = content.split("---")
                if len(parts) >= 3:
                    front_matter = parts[1]
                    data = yaml.safe_load(front_matter) or {}
                    if "topic" in data and data["topic"]:
                        recent_topics.add(str(data["topic"]).strip().lower())
        except Exception:
            continue

    return recent_topics


def select_topic_and_category(config_path):
    """Selects a topic and category while excluding recently posted topics."""
    if not Path(config_path).exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    recent_topics = get_recent_topics(days=10)
    all_candidates = []

    # Handle structure 1: { "categories": [ { "name": "Cloud", "topics": [...] } ] }
    if "categories" in config and isinstance(config["categories"], list):
        for cat in config["categories"]:
            cat_name = cat.get("name", "General")
            for topic in cat.get("topics", []):
                all_candidates.append({"topic": topic, "category": cat_name})

    # Handle structure 2: { "topics": [ { "name": "Azure", "category": "Cloud" } ] } or { "topics": { "Cloud": [...] } }
    elif "topics" in config:
        topics_data = config["topics"]
        if isinstance(topics_data, list):
            for item in topics_data:
                if isinstance(item, dict):
                    all_candidates.append({
                        "topic": item.get("name", item.get("topic")),
                        "category": item.get("category", "IT")
                    })
                elif isinstance(item, str):
                    all_candidates.append({"topic": item, "category": "IT"})
        elif isinstance(topics_data, dict):
            for cat_name, t_list in topics_data.items():
                if isinstance(t_list, list):
                    for t in t_list:
                        all_candidates.append({"topic": t, "category": cat_name})

    # Handle structure 3: Direct dictionary of categories { "Cloud": ["Azure", "AWS"], "DevOps": ["Git"] }
    elif isinstance(config, dict):
        for cat_name, t_list in config.items():
            if isinstance(t_list, list):
                for t in t_list:
                    all_candidates.append({"topic": t, "category": cat_name})

    if not all_candidates:
        # Emergency fallback if config parsing fails to find items
        all_candidates = [
            {"topic": "Git and GitHub", "category": "DevOps"},
            {"topic": "Azure Cloud Security", "category": "Cloud"},
            {"topic": "Linux Terminal Basics", "category": "SysAdmin"},
        ]

    # Filter out topics used in the last 10 days
    fresh_candidates = [
        c for c in all_candidates if c["topic"].strip().lower() not in recent_topics
    ]

    selected = random.choice(fresh_candidates if fresh_candidates else all_candidates)
    return selected["topic"], selected["category"]


def generate_post(topic, category):
    """Generates LinkedIn post content using primary and fallback Gemini models."""
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
When generating Python code examples for networking or API monitoring, 
do NOT use actual external URLs or http://example.com unless necessary. 
Instead, use generic placeholders such as:
- 'https://api.yourcompany.local/health'
- 'http://127.0.0.1:8080/status'
- 'http://localhost/health'

Return only the post text.
"""

    max_attempts = 5
    delays = [10, 20, 40, 80]

    models_to_try = [MODEL, FALLBACK_MODEL]

    for model_index, model_name in enumerate(models_to_try):
        print(f"Using Gemini model: {model_name}")

        for attempt in range(1, max_attempts + 1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )

                if not response or not response.text:
                    raise RuntimeError("Gemini returned an empty response")

                return response.text.strip()

            except (errors.ServerError, errors.ClientError) as exc:
                status_code = getattr(exc, "code", None)

                # 404 = Model name not available/deprecated. Skip to next model immediately.
                if isinstance(exc, errors.ClientError) and status_code == 404:
                    print(f"[WARNING] Model {model_name} returned 404 NOT_FOUND.")
                    if model_index < len(models_to_try) - 1:
                        print(f"Switching immediately to fallback model: {FALLBACK_MODEL}")
                        break
                    raise

                # 429 = Quota exhausted. Skip to next model immediately.
                if isinstance(exc, errors.ClientError) and status_code == 429:
                    print(f"[WARNING] {model_name} quota exhausted (429).")
                    if model_index < len(models_to_try) - 1:
                        print(f"Switching immediately to fallback model: {FALLBACK_MODEL}")
                        break
                    raise

                # 503 / Transient Server Errors: Retry with backoff
                if attempt == max_attempts:
                    if model_index < len(models_to_try) - 1:
                        print(f"[WARNING] {model_name} unavailable after {max_attempts} attempts.")
                        print(f"Switching to fallback model: {FALLBACK_MODEL}")
                        break
                    print("[ERROR] All Gemini models unavailable.")
                    raise

                delay = delays[attempt - 1]
                print(f"Gemini server error on {model_name} (attempt {attempt}/{max_attempts}). Retrying in {delay}s...")
                time.sleep(delay)

            except Exception as exc:
                print(
                    f"[ERROR] Gemini generation failed using {model_name}: {exc}"
                )
                raise


def save_work_draft(content, topic, category, output_dir, attempt=1):
    """Saves the generated post as a markdown file with required front matter."""
    today = datetime.now().strftime("%Y-%m-%d")
    slug = (
        topic.lower()
        .replace(" ", "-")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "-")
    )
    filename = f"{today}-{slug}-attempt-{attempt}.md"

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    file_path = out_path / filename

    # Clean category/topic tags for front matter
    tag_topic = topic.lower().replace(" ", "").replace("(", "").replace(")", "").replace("-", "")
    tag_cat = category.lower().replace(" ", "").replace("(", "").replace(")", "").replace("-", "")

    front_matter = f"""---
title: "AI-generated post about {topic}"
topic: "{topic}"
category: "{category}"
status: "draft"
approval: "pending"
publish: false
platforms:
  - linkedin
tags:
  - {tag_cat}
  - {tag_topic}
  - tech
created_at: '{today}'
---

{content}
"""
    file_path.write_text(front_matter, encoding="utf-8")
    print(f"Content generated: {file_path}")
    return file_path

def main():
    parser = argparse.ArgumentParser(description="Generate AI LinkedIn Post")
    parser.add_argument("--output-dir", default="content/work", help="Directory to output draft")
    parser.add_argument("--attempt", type=int, default=1, help="Attempt number")
    args = parser.parse_args()

    config_path = BASE_DIR / "config" / "topics.yaml"
    topic, category = select_topic_and_category(config_path)

    print(f"Selected topic: {topic} ({category})")
    post_content = generate_post(topic, category)

    save_work_draft(post_content, topic, category, args.output_dir, args.attempt)


if __name__ == "__main__":
    main()