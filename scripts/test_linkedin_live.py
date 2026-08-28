from publishers.linkedin import LinkedInPublisher


TEST_MESSAGE = """🤖 AI Content Automation — first live test

I'm testing a small automation project that generates useful IT content and can publish it automatically.

This is a controlled test of the LinkedIn publishing pipeline.

#IT #Automation #DevOps"""


def main():
    publisher = LinkedInPublisher(dry_run=False)

    post_id = publisher.publish(TEST_MESSAGE)

    print(f"LinkedIn post created successfully: {post_id}")


if __name__ == "__main__":
    main()
