import os

import requests
from dotenv import load_dotenv

from publishers.base import Publisher


class LinkedInPublisher(Publisher):
    """Publisher for LinkedIn personal or organization posts."""

    API_URL = "https://api.linkedin.com/rest/posts"

    def __init__(self, dry_run=True):
        load_dotenv()

        self.access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        self.author_urn = os.getenv("LINKEDIN_AUTHOR_URN")
        self.version = os.getenv("LINKEDIN_VERSION", "202607")
        self.dry_run = dry_run

        if not self.access_token:
            raise RuntimeError("LINKEDIN_ACCESS_TOKEN is not set")

        if not self.author_urn:
            raise RuntimeError("LINKEDIN_AUTHOR_URN is not set")

    def publish(self, content: str) -> str:
        payload = {
            "author": self.author_urn,
            "commentary": content,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        if self.dry_run:
            print("LINKEDIN DRY RUN")
            print("================")
            print(f"Author: {self.author_urn}")
            print(f"API: {self.API_URL}")
            print("Payload:")
            print(payload)
            print("================")
            return "dry-run"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": self.version,
        }

        response = requests.post(
            self.API_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )

        if response.status_code != 201:
            raise RuntimeError(
                f"LinkedIn API error {response.status_code}: "
                f"{response.text}"
            )

        post_id = response.headers.get("x-restli-id")

        if not post_id:
            raise RuntimeError(
                "LinkedIn returned 201 but no x-restli-id header"
            )

        return post_id
