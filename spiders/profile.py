import scrapy
import json
import os
from scrapy_playwright.page import PageMethod
from scrapy.utils.project import get_project_settings

settings=get_project_settings()

def should_abort_request(request):
    return request.resource_type in ["image", "fetch", "font", "media", "other"] or ".jpg" in request.url

class LinkedInSpider(scrapy.Spider):
    name = 'profile'
    allowed_domains = ["linkedin.com"]
    custom_settings = {
        "PLAYWRIGHT_ABORT_REQUEST": should_abort_request,
    }

    def start_requests(self):
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        }

        url = "profil_url"
        yield scrapy.Request(
            url,
            headers=headers,
            meta=dict(
                playwright=True,
                playwright_include_page=True,
                playwright_context_kwargs={
                    "storage_state": settings.get('STORAGE_PATH') if os.path.exists(settings.get('STORAGE_PATH')) else None,
                },
                playwright_page_methods=[
                    PageMethod("wait_for_load_state", state="domcontentloaded")
                ],
            )
        )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        
        # Save storage state
        storage_state = await page.context.storage_state()
        with open(settings.get('STORAGE_PATH'), 'w') as f:
            json.dump(storage_state, f)

        name = response.css('h1.text-heading-xlarge::text').get().strip()
        headline = response.css('div.text-body-medium.break-words::text').get().strip()
        location = response.css('span.text-body-small.inline.t-black--light.break-words::text').get().strip()
        print("_____________________-----------------------------------name", name)
        page.wait_for_timeout(100*1000)

        item = {
            'name': name,
            'headline': headline,
            'location': location,
        }

        # Check if there is a "Contact info" link and follow it
        contact_info_link = response.css('a#top-card-text-details-contact-info::attr(href)').get()
        if contact_info_link:
            await page.click('a#top-card-text-details-contact-info')
            await page.wait_for_selector('div.pv-profile-section__section-info.section-info')

            linkedin_url = await page.locator('section.pv-contact-info__contact-type a.link-without-visited-state').get_attribute('href')
            item['contact_info'] = {
                'linkedin_url': linkedin_url,
            }

            await page.close()

            yield item
        else:
            print("----------------------------------contact_info_link = None")
            yield item

    async def parse_contact_info(self, response):
        item = response.meta['item']
        print("-------------------------------------------parsing contact")
        contact_details = response.xpath('//section[contains(@class, "pv-contact-info__contact-type")]//a[contains(@class, "link-without-visited-state")]/@href').getall()
        item['contact_info'] = contact_details

        yield item
