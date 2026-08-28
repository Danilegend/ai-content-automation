import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

import requests


def send_telegram_message(message: str) -> bool:
    """Sends an HTML-formatted message to your Telegram Chat."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print(
            "[NOTIFIER] Telegram credentials missing. Skipping notification."
        )
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code == 200:
            print("[NOTIFIER] Telegram message sent successfully!")
            return True
        else:
            print(
                f"[NOTIFIER] Telegram API error ({response.status_code}): {response.text}"
            )
            return False
    except Exception as e:
        print(f"[NOTIFIER] Failed to send Telegram alert: {e}")
        return False


if __name__ == "__main__":
    send_telegram_message(
        "🤖 <b>AI Content Automation</b>: Local notifier test message!"
    )