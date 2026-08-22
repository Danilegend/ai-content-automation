import sys
from pathlib import Path

import yaml

from publishers.linkedin import LinkedInPublisher
from scripts.config_loader import load_publishing_config


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


def publish_to_linkedin(metadata, body):
    linkedin_state = metadata.get("linkedin", {})

    if linkedin_state.get("status") == "published":
        print("⏭️ LinkedIn: already published")
        return linkedin_state.get("post_id")

    publisher = LinkedInPublisher(dry_run=False)

    post_id = publisher.publish(body)

    return post_id


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.publish <file>")
        sys.exit(1)

    path = Path(sys.argv[1])

    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    metadata, body = load_post(path)

    print("=" * 60)
    print(f"PUBLISHING: {path.name}")
    print("=" * 60)

    if metadata.get("status") != "approved":
        raise RuntimeError("Content is not approved")

    if metadata.get("approval") != "approved":
        raise RuntimeError("Approval state is not approved")

    config = load_publishing_config()

    platforms = config.get("platforms", {})

    # LinkedIn
    linkedin = platforms.get("linkedin", {})

    if linkedin.get("enabled") and linkedin.get("publish"):
        print("\nLinkedIn: ENABLED")

        post_id = publish_to_linkedin(metadata, body)

        metadata["linkedin"] = {
            "status": "published",
            "post_id": post_id,
        }

        print(f"✅ LinkedIn complete: {post_id}")

    else:
        print("\nLinkedIn: DISABLED")

    # Future platforms
    for platform in [
        "x",
        "reddit",
        "telegram",
        "bluesky",
        "mastodon",
        "discord",
    ]:
        platform_config = platforms.get(platform, {})

        if (
            platform_config.get("enabled")
            and platform_config.get("publish")
        ):
            print(
                f"\n⚠️ {platform}: enabled but publisher "
                "is not implemented yet"
            )
        else:
            print(f"{platform}: disabled")

    print("\n" + "=" * 60)
    print("PUBLISHING COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
