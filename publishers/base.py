from abc import ABC, abstractmethod


class Publisher(ABC):
    """Base interface for all social-media publishers."""

    @abstractmethod
    def publish(self, content: str) -> str:
        """
        Publish content and return a platform-specific post ID.
        """
        raise NotImplementedError
