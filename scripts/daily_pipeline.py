import subprocess
import sys
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
GENERATE_SCRIPT = BASE_DIR / "scripts" / "generate_content.py"
VALIDATE_SCRIPT = BASE_DIR / "scripts" / "validate_content.py"
DRAFTS_DIR = BASE_DIR / "content" / "drafts"


def run_command(command):
    result = subprocess.run(
        command,
        cwd=BASE_DIR,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}"
        )


def find_today_draft():
    today = datetime.now().strftime("%Y-%m-%d")

    files = sorted(DRAFTS_DIR.glob(f"{today}-*.md"))

    if not files:
        return None

    return files[0]


def main():
    print("=" * 60)
    print("AI CONTENT AUTOMATION - DAILY PIPELINE")
    print("=" * 60)

    print("\n[1/2] Generating content...")
    run_command([sys.executable, str(GENERATE_SCRIPT)])

    draft = find_today_draft()

    if draft is None:
        print("\nNo new draft was created today.")
        print("Pipeline finished safely.")
        return

    print(f"\n[2/2] Validating: {draft.name}")
    run_command(
        [
            sys.executable,
            str(VALIDATE_SCRIPT),
            str(draft),
        ]
    )

    print("\n" + "=" * 60)
    print("✅ DAILY PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    main()
