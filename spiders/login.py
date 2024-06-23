import scrapy
import json
import random
from scrapy_playwright.page import PageMethod
from scrapy.utils.project import get_project_settings

settings=get_project_settings()


class LoginSpider(scrapy.Spider):
    name = 'login'
    allowed_domains = ['linkedin.com']
    start_urls = ['https://www.linkedin.com/uas/login']

    def start_requests(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.linkedin.com',
            'Referer': 'https://www.linkedin.com/login',
        }
        yield scrapy.Request(
            self.start_urls[0],
            headers=headers,
            meta=dict(
                playwright=True,
                playwright_include_page=True,
                playwright_page_methods=[
                    PageMethod("wait_for_load_state", state="domcontentloaded"),
                ],
            )
        )

    async def parse(self, response):
        page = response.meta["playwright_page"]

        # Fill in login form and submit
        await page.fill('input#username', 'username')
        await page.fill('input#password', 'password')

        random_wait_time = random.uniform(1, 5)
        await page.wait_for_timeout(random_wait_time * 1000)
        await page.click('button[type=submit]')
        await page.wait_for_load_state('domcontentloaded')

        
        feed_url = 'https://www.linkedin.com/feed/'
        max_wait_time = 30  
        check_interval = 1  

        for _ in range(max_wait_time):
            if page.url == feed_url:
                break
            await page.wait_for_timeout(check_interval * 100000)
        else:
            self.logger.error(f"Did not redirect to {feed_url} within {max_wait_time} seconds.")
            await page.close()
            return

        # Save storage state
        storage_state = await page.context.storage_state()
        with open(settings.get('STORAGE_PATH'), 'w') as f:
            json.dump(storage_state, f)

        # Close the page
        await page.close()
        self.logger.info("Login successful and storage state saved.")
