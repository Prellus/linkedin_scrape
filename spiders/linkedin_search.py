import scrapy
from scrapy_playwright.page import PageMethod

class LinkedInSearchSpider(scrapy.Spider):
    name = 'linkedin_search'
    allowed_domains = ['linkedin.com']
    start_urls = ['linkedin search url']
    
    custom_settings = {
        "PLAYWRIGHT_ABORT_REQUEST": lambda request: request.resource_type in ["image", "font", "media", "other"],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_count = 1
        self.max_pages = 3 

    def start_requests(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        }
        
        for url in self.start_urls:
            yield scrapy.Request(
                url,
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
        
        # Extract profile URLs
        profile_urls = await page.eval_on_selector_all(
            'li.reusable-search__result-container a.app-aware-link',
            'elements => elements.map(el => el.href)'
        )

        for profile_url in profile_urls:
            yield {
                'profile_url': profile_url
            }
        
        if self.page_count < self.max_pages:
            self.page_count += 1

            # Log the current state
            self.logger.info(f"Attempting to go to page {self.page_count}")

            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(2000) 

            next_page_button = await page.query_selector('button.artdeco-pagination__button--next')

            if next_page_button:
                await next_page_button.click()
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_selector('li.reusable-search__result-container', state='attached')  # Ensure new content is loaded

                # Get the updated page content
                new_response = await page.content()
                response.meta['playwright_page_content'] = new_response
                response.meta['playwright_page_url'] = page.url
                yield scrapy.Request(
                    url=page.url,
                    callback=self.parse,
                    meta=response.meta
                )
            else:
                self.logger.info(f"Next button not found on page {self.page_count}")
        else:
            self.logger.info("Reached maximum number of pages to crawl")