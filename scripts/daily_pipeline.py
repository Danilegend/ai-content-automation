import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

# Ensure project root is in sys.path so 'scripts.notifier' can be found
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Now import the notifier
from scripts.notifier import send_telegram_message

CONTENT_LOOP = BASE_DIR / "scripts" / "content_loop.py"
VALIDATE_SCRIPT = BASE_DIR / "scripts" / "validate_content.py"
APPROVE_SCRIPT = BASE_DIR / "scripts" / "approve_content.py"
PUBLISH_SCRIPT = BASE_DIR / "scripts" / "publish.py"

DRAFTS_DIR = BASE_DIR / "content" / "drafts"
CONFIG_FILE = BASE_DIR / "config" / "publishing.yaml"


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


def load_config():
    with CONFIG_FILE.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def find_today_draft():
    today = datetime.now().strftime("%Y-%m-%d")

    files = sorted(
        DRAFTS_DIR.glob(f"{today}-*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not files:
        return None

    return files[0]


def set_publish_flag(path: Path, enabled: bool):
    text = path.read_text(encoding="utf-8")

    if enabled:
        text = text.replace(
            "publish: false",
            "publish: true",
        )

    path.write_text(text, encoding="utf-8")


def main():
    print("=" * 60)
    print("AI CONTENT AUTOMATION - DAILY PIPELINE")
    print("=" * 60)

    try:
        config = load_config()
        approval_mode = config.get("approval_mode", "manual")
        print(f"\nApproval mode: {approval_mode}")

        print("\n[1/3] Generating and reviewing content...")
        run_command([sys.executable, "-m", "scripts.content_loop"])

        draft = find_today_draft()

        if draft is None:
            msg = "⚠️ *AI Content Engine Alert*\n\nNo approved draft was generated today (quality loop rejected all attempts or API issue)."
            print(f"\n{msg}")
            send_telegram_message(msg)
            print("Pipeline finished safely.")
            return
        # ... middle steps ...

        if approval_mode != "automatic":
            msg = f"ℹ️ <b>AI Content Engine</b>\n\nDraft <code>{draft.name}</code> generated, but pipeline is in <i>manual</i> approval mode. Awaiting review."
            print(f"\n{msg}")
            send_telegram_message(msg)
            return

        # ... publishing step ...

        send_telegram_message(
            f"🚀 <b>AI Content Engine Success</b>\n\nPublished draft: <code>{draft.name}</code> to LinkedIn."
        )

    except Exception as e:
        error_msg = f"🚨 <b>AI Content Engine Pipeline Error</b>\n\nPipeline aborted with error:\n<code>{str(e)}</code>"
        print(f"\n{error_msg}")
        send_telegram_message(error_msg)
        sys.exit(1)

        print(f"\nFinal draft: {draft.name}")

        print("\n[2/3] Validating content...")
        run_command([sys.executable, str(VALIDATE_SCRIPT), str(draft)])

        if approval_mode == "automatic":
            print("\nApproving quality-approved content...")
            run_command([sys.executable, str(APPROVE_SCRIPT), str(draft)])
            set_publish_flag(draft, enabled=True)
        else:
            msg = f"ℹ️ *AI Content Engine*\n\nDraft `{draft.name}` generated, but pipeline is in *manual* approval mode. Awaiting review."
            print(f"\n{msg}")
            send_telegram_message(msg)
            return

        print("\n[3/3] Publishing content...")
        run_command([sys.executable, "-m", "scripts.publish", str(draft)])

        print("\n" + "=" * 60)
        print("✅ DAILY PIPELINE COMPLETED")
        print("=" * 60)

        # Notify Success
        send_telegram_message(
            f"🚀 *AI Content Engine Success*\n\nPublished draft: `{draft.name}` to LinkedIn."
        )

    except Exception as e:
        error_msg = f"🚨 *AI Content Engine Pipeline Error*\n\nPipeline aborted with error:\n`{str(e)}`"
        print(f"\n{error_msg}")
        send_telegram_message(error_msg)
        sys.exit(1)


if __name__ == "__main__":
    main()