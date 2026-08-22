import shutil
import subprocess
import sys
from pathlib import Path

import yaml


BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG_FILE = (
    BASE_DIR / "config" / "content_quality.yaml"
)

GENERATE_SCRIPT = (
    BASE_DIR / "scripts" / "generate_content.py"
)

REVIEW_SCRIPT = (
    BASE_DIR / "scripts" / "review_content.py"
)

QUALITY_GATE = (
    BASE_DIR / "scripts" / "quality_gate.py"
)

WORK_DIR = BASE_DIR / "content" / "work"
DRAFTS_DIR = BASE_DIR / "content" / "drafts"


def load_config():
    with CONFIG_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return yaml.safe_load(file)


def run(command):
    result = subprocess.run(
        command,
        cwd=BASE_DIR,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code "
            f"{result.returncode}"
        )


def find_latest_work_file():
    files = sorted(
        WORK_DIR.glob("*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not files:
        return None

    return files[0]


def get_score(path):
    text = path.read_text(
        encoding="utf-8"
    )

    parts = text.split("---", 2)

    if len(parts) != 3:
        return None

    metadata = yaml.safe_load(parts[1])

    review = metadata.get(
        "review",
        {},
    )

    return review.get(
        "overall_score"
    )


def clean_work_directory():
    WORK_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for file in WORK_DIR.glob("*.md"):
        file.unlink()


def main():
    config = load_config()

    max_attempts = int(
        config.get(
            "max_generation_attempts",
            3,
        )
    )

    minimum_score = float(
        config.get(
            "minimum_score",
            7,
        )
    )

    print("=" * 60)
    print("AI CONTENT QUALITY LOOP")
    print("=" * 60)

    clean_work_directory()

    for attempt in range(
        1,
        max_attempts + 1,
    ):

        print(
            f"\nGeneration attempt "
            f"{attempt}/{max_attempts}"
        )

        print(
            "\n[1] Generating content..."
        )

        run(
            [
                sys.executable,
                str(GENERATE_SCRIPT),
                "--output-dir",
                str(WORK_DIR),
            ]
        )

        draft = find_latest_work_file()

        if draft is None:
            raise RuntimeError(
                "No draft was generated."
            )

        print(
            f"Work draft: {draft.name}"
        )

        print(
            "\n[2] Reviewing content..."
        )

        run(
            [
                sys.executable,
                str(REVIEW_SCRIPT),
                str(draft),
            ]
        )

        score = get_score(draft)

        if score is None:
            raise RuntimeError(
                "Reviewer did not produce a score."
            )

        score = float(score)

        print(
            f"\nQuality score: "
            f"{score:.1f}/10"
        )

        if score >= minimum_score:

            print(
                "\n✅ Content meets "
                "quality threshold."
            )

            print(
                "\n[3] Applying quality gate..."
            )

            run(
                [
                    sys.executable,
                    str(QUALITY_GATE),
                    str(draft),
                ]
            )

            DRAFTS_DIR.mkdir(
                parents=True,
                exist_ok=True,
            )

            final_path = (
                DRAFTS_DIR / draft.name
            )

            shutil.copy2(
                draft,
                final_path,
            )

            print(
                f"\n🎉 FINAL CONTENT READY"
            )

            print(
                f"Final draft: {final_path}"
            )

            clean_work_directory()

            return

        print(
            f"\n❌ Score below "
            f"{minimum_score}/10."
        )

        if attempt < max_attempts:
            print(
                "Preparing another "
                "generation attempt..."
            )

    clean_work_directory()

    print("\n" + "=" * 60)
    print("❌ MAXIMUM ATTEMPTS REACHED")
    print("=" * 60)

    raise RuntimeError(
        "No generated post reached "
        "the required quality score."
    )


if __name__ == "__main__":
    main()
