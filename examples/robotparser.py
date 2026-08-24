import asyncio
import urllib.robotparser


async def main():
    # Initialize the parser
    rp = urllib.robotparser.RobotFileParser()

    # Set the URL for the site's robots.txt
    rp.set_url("https://www.scrapingcourse.com/robots.txt")

    # Read and parse the robots.txt file
    rp.read()

    # Define your user agent and target URL to check
    user_agent = "*"
    target_url = "https://www.scrapingcourse.com/ecommerce/page/2/"

    # Check permission
    can_fetch = rp.can_fetch(user_agent, target_url)

    if can_fetch:
        print(f"Allowed to scrape: {target_url}")
    else:
        print(f"Blocked by robots.txt: {target_url}")


asyncio.run(main())
