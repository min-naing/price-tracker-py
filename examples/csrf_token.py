import asyncio
import logging

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

LOGIN_URL = "https://www.scrapingcourse.com/login/csrf"
PROTECTED_URL = "http://www.scrapingcourse.com/dashboard"

USERNAME = "admin@example.com"
PASSWORD = "password"


async def debug_csrf_token() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        # page.on(
        #     "console",
        #     lambda msg: logger.info("CONSOLE: %s %s", msg.type, msg.text),
        # )

        # page.on(
        #     "request",
        #     lambda request: logger.info(
        #         "REQUEST: %s %s",
        #         request.method,
        #         request.url,
        #     ),
        # )

        # page.on(
        #     "response",
        #     lambda response: logger.info(
        #         "RESPONSE: %s %s",
        #         response.status,
        #         response.url,
        #     ),
        # )

        # page.on(
        #     "requestfailed",
        #     lambda request: logger.info(
        #         "FAILED: %s %s",
        #         request.url,
        #         request.failure,
        #     ),
        # )

        await page.goto(LOGIN_URL)

        await page.get_by_label("Email Address").fill(USERNAME)
        await page.get_by_label("Password").fill(PASSWORD)

        csrf_token = await page.locator('input[name="_token"]').input_value()

        logger.info(
            "CSRF token exists: %s",
            bool(csrf_token),
        )

        async with page.expect_request(
            lambda request: request.method == "POST" and "/login" in request.url
        ) as request_info:
            await page.get_by_role(
                "button",
                name="Login",
            ).click()
            request = await request_info.value
            # request = response.request

            logger.info(
                "Login URL: %s",
                request.url,
            )

            logger.info(
                "POST data: %s",
                request.post_data,
            )

            # headers = await request.all_headers()

            # logging.info("Request URL: %s", request.url)
            # logging.info("Request method: %s", request.method)
            # logging.info("Request headers: \n%s", pprint.pformat(headers, indent=4))
            # logging.info(
            #     "X-CSRF-Token present: %s",
            #     "x-csrf-token" in headers,
            # )
            # logging.info("Response status: %s", response.status)

            # if not response.ok:
            #     logging.error(
            #         "Response body: \n%s",
            #         await response.text(),
            #     )

        await page.wait_for_timeout(3000)

        await browser.close()


async def unlock_csrf_token() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)

        context = await browser.new_context()
        page = await context.new_page()

        # 1. Visit login page
        await page.goto(LOGIN_URL, wait_until="domcontentloaded")

        # 2. Extract CSRF token from the HTML
        csrf_token = await page.locator('input[name="_token"]').input_value()

        logger.info(
            "CSRF token exists: %s",
            bool(csrf_token),
        )

        # 3. Send login request manually
        response = await context.request.post(
            LOGIN_URL,
            form={
                "_token": csrf_token,
                "email": USERNAME,
                "password": PASSWORD,
            },
        )

        logger.info(
            "Login response status: %s",
            response.status,
        )

        # 4. Check the final page
        logger.info(
            "Login response URL: %s",
            response.url,
        )

        cookies = await context.cookies()

        for cookie in cookies:
            logger.info(
                "Cookie: %s",
                cookie["name"],  # pyright: ignore[reportTypedDictNotRequiredAccess]
            )

        # 5. Open a page using the same browser context
        await page.goto(response.url, wait_until="domcontentloaded")

        logout_link = page.get_by_text("Logout")

        if await logout_link.count():
            logger.info("Login successful")
        else:
            logger.error("Login may have failed")

        await page.wait_for_timeout(3000)

        logger.info(
            "Current page URL: %s",
            page.url,
        )

        await browser.close()


def main():
    logging.basicConfig(level=logging.INFO)
    asyncio.run(unlock_csrf_token())


if __name__ == "__main__":
    main()
