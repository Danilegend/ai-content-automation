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
from google.genai import types

# --- ADD THESE TWO LINES ---
from dotenv import load_dotenv
load_dotenv()

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# --- Model Configuration ---
MODEL = "gemini-3.5-flash"
FALLBACK_MODELS = [
    "gemini-3.5-flash-lite", 
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.8-flash",
    "gemini-2.5-flash",
]


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

    if "categories" in config and isinstance(config["categories"], list):
        for cat in config["categories"]:
            cat_name = cat.get("name", "General")
            for topic in cat.get("topics", []):
                all_candidates.append({"topic": topic, "category": cat_name})
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
    elif isinstance(config, dict):
        for cat_name, t_list in config.items():
            if isinstance(t_list, list):
                for t in t_list:
                    all_candidates.append({"topic": t, "category": cat_name})

    if not all_candidates:
        all_candidates = [
            {"topic": "Git and GitHub", "category": "DevOps"},
            {"topic": "Azure Cloud Security", "category": "Cloud"},
            {"topic": "Linux Terminal Basics", "category": "SysAdmin"},
        ]

    fresh_candidates = [
        c for c in all_candidates if c["topic"].strip().lower() not in recent_topics
    ]

    selected = random.choice(fresh_candidates if fresh_candidates else all_candidates)
    return selected["topic"], selected["category"]


def make_api_call(client, prompt, models_to_try):
    """Handles the API call, rate limits, and fallbacks."""
    max_attempts = 6
    delays = [15, 30, 45, 60, 90, 120]

    for current_model in models_to_try:
        print(f"  -> Calling Gemini API ({current_model})...")
        
        for attempt in range(1, max_attempts + 1):
            try:
                chat = client.chats.create(model=current_model)
                response = chat.send_message(prompt)

                if not response or not response.text:
                    raise RuntimeError("Gemini returned an empty response")

                return response.text.strip()

            except Exception as exc:
                status_code = getattr(exc, "code", getattr(exc, "status_code", None))

                if status_code == 429:
                    wait_time = 45
                    print(f"  [RATE LIMIT 429] Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                if attempt == max_attempts:
                    if current_model == models_to_try[-1]:
                        raise exc
                    else:
                        break 

                delay = delays[attempt - 1]
                print(f"  Gemini API issue (attempt {attempt}). Retrying in {delay}s...")
                time.sleep(delay)

    raise RuntimeError("Content generation failed after all attempts.")

def generate_post(topic, category):
    """Generates post content using a TWO-STAGE process (Strategist + Writer)."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(api_version="v1")
    )

    models_to_try = [MODEL] + FALLBACK_MODELS

    # ==========================================
    # STAGE 1: THE STRATEGIST
    # ==========================================
    post_styles = [
        "A personal story / lesson learned (First person: 'I', 'my team')",
        "An unpopular opinion or myth-busting (Direct, slightly provocative)",
        "A behind-the-scenes look at how something actually works (Analytical)",
        "A tactical checklist or 'how-to' disguised as a story (Practical)",
        "A career observation (Objective, third-person advice)"
    ]
    selected_style = random.choice(post_styles)

    strategist_prompt = f"""
    You are a Senior Content Strategist for a tech professional's LinkedIn profile.
    The target audience is early-to-mid career IT professionals.
    
    Your task is to brainstorm a highly engaging angle for a post about:
    Topic: {topic}
    Category: {category}

    For this post, you MUST use this specific format/style: 
    **{selected_style}**

    DO NOT write the post yet. Just answer these questions in 2-3 sentences:
    1. What is a common frustration or misconception related to this topic?
    2. What is a specific, non-obvious lesson someone could learn from it?
    3. Give a 1-sentence "hook" that fits the requested style and does NOT sound like an AI.
    """

    print("Stage 1: Thinking of a human angle...")
    # THIS IS THE MISSING LINE THAT CREATES THE 'angle' VARIABLE
    angle = make_api_call(client, strategist_prompt, models_to_try) 
    print(f"\nAngle selected:\n{angle}\n")

    # ==========================================
    # STAGE 2: THE WRITER
    # ==========================================
    writer_prompt = f"""
    You are an experienced IT professional writing a LinkedIn post.
    
    Topic: {topic}
    Category: {category}
    
    Here is the strategic angle you MUST use:
    ---
    {angle}
    ---

    Requirements:
    - The requested style for this post is: **{selected_style}**
    - Tone: Conversational, professional, and slightly opinionated. Like a colleague sharing wisdom over coffee.
    - DO NOT use AI clichés. 
      * BANNED OPENINGS: "Here is...", "Stop doing X...", "The fastest way to...", "In the world of...", "I spent my first..."
      * BANNED FORMAT: Do not use bulleted lists with bold headers. Write in paragraphs.
    - DO NOT include code blocks or terminal commands unless they are absolutely necessary.
    - Instead of a generic question like "What do you think?", ask a specific question.
    - Include 3 to 5 relevant hashtags.
    - Keep it under 250 words.

    Return ONLY the post text. Do not include quotes around the output.
    """

    print("Stage 2: Writing the human-sounding post...")
    post_content = make_api_call(client, writer_prompt, models_to_try)
    
    return post_content


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

    print(f"\nSelected topic: {topic} ({category})")
    post_content = generate_post(topic, category)

    save_work_draft(post_content, topic, category, args.output_dir, args.attempt)
    print("\n✅ Generation complete.")

if __name__ == "__main__":
    main()