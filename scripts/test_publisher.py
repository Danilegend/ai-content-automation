from publishers.base import Publisher


class TestPublisher(Publisher):
    def publish(self, content: str) -> str:
        print("TEST PUBLISHER")
        print("----------------")
        print(content)
        print("----------------")
        return "test-post-001"


def main():
    publisher = TestPublisher()

    post_id = publisher.publish(
        "This is a safe publisher architecture test."
    )

    print(f"Returned post ID: {post_id}")


if __name__ == "__main__":
    main()
