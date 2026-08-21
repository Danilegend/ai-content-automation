from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "content" / "drafts"


def generate_content(topic: str, category: str) -> Path:
    today = datetime.now().strftime("%Y-%m-%d")

    content = f"""---
title: "Why {topic} Matters for IT Professionals"
topic: "{topic}"
category: "{category}"
status: "draft"
publish: false
platforms:
  - linkedin
tags:
  - "{topic}"
  - "IT"
  - "Technology"
created_at: "{today}"
---

# Why {topic} Matters for IT Professionals

Understanding **{topic}** is an important skill for modern IT professionals.

In today's technology environment, practical knowledge of {topic} can help IT professionals troubleshoot problems, improve systems, automate repetitive tasks, and build stronger technical foundations.

## Key Takeaway

Learning {topic} is not only about knowing commands or tools. The real value comes from understanding **why** and **when** to use it.

## Call to Action

What is one thing about {topic} that you would recommend every IT professional learn?
"""

    output_file = OUTPUT_DIR / f"{today}-{topic.lower().replace(' ', '-')}.md"
    output_file.write_text(content, encoding="utf-8")

    return output_file


if __name__ == "__main__":
    file_path = generate_content("Linux", "IT Support")
    print(f"Content generated: {file_path}")
