from pathlib import Path

import yaml


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config" / "publishing.yaml"


def load_publishing_config():
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"Publishing configuration not found: {CONFIG_FILE}"
        )

    with CONFIG_FILE.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ValueError("Invalid publishing configuration")

    return config


def platform_enabled(platform: str) -> bool:
    config = load_publishing_config()

    platform_config = config.get("platforms", {}).get(platform, {})

    return (
        platform_config.get("enabled", False)
        and platform_config.get("publish", False)
    )


if __name__ == "__main__":
    config = load_publishing_config()

    print("Publishing configuration loaded")
    print(f"Approval mode: {config.get('approval_mode')}")

    for platform, settings in config.get("platforms", {}).items():
        enabled = settings.get("enabled", False)
        publish = settings.get("publish", False)

        print(
            f"{platform}: "
            f"enabled={enabled}, "
            f"publish={publish}"
        )
