"""
Hemnet spider for scraping apartment listings from hemnet.se.

This spider handles:
1. Searching through result pages
2. Extracting apartment listing URLs
3. Following links to detail pages
4. Extracting apartment data according to defined KPIs
"""

import scrapy
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs
from pidgeon.items import ApartmentItemLoader, HemnetApartmentItem


class HemnetSpider(scrapy.Spider):
    name = 'hemnet'
    allowed_domains = ['hemnet.se']

    # Default search URLs - can be overridden via spider arguments
    start_urls = [
        'https://www.hemnet.se/bostader?location_ids%5B%5D=17744',  # Stockholm
    ]

    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5,
        'CONCURRENT_REQUESTS': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, search_url=None, *args, **kwargs):
        super(HemnetSpider, self).__init__(*args, **kwargs)
        if search_url:
            self.start_urls = [search_url]

    def parse(self, response):
        """
        Parse search result pages and extract apartment listing URLs.
        """
        self.logger.info(f'Parsing search results from {response.url}')

        # Extract listing URLs from search results
        listing_urls = response.css('a[href*="/bostad/"]::attr(href)').getall()

        if not listing_urls:
            self.logger.warning(f'No listing URLs found on {response.url}')
            # Try alternative selectors
            listing_urls = response.css('.listing-card a::attr(href)').getall()

        for listing_url in listing_urls:
            absolute_url = urljoin(response.url, listing_url)
            yield response.follow(
                absolute_url,
                callback=self.parse_apartment,
                meta={'search_url': response.url}
            )

        # Follow pagination links
        next_page = response.css('a[rel="next"]::attr(href)').get()
        if next_page:
            yield response.follow(
                next_page,
                callback=self.parse,
                meta={'search_url': response.url}
            )
        else:
            # Try alternative pagination selector
            next_page = response.css('.pagination .next::attr(href)').get()
            if next_page:
                yield response.follow(
                    next_page,
                    callback=self.parse,
                    meta={'search_url': response.url}
                )

    def parse_apartment(self, response):
        """
        Parse individual apartment detail pages and extract all KPI data.
        """
        self.logger.info(f'Parsing apartment from {response.url}')

        loader = ApartmentItemLoader(item=HemnetApartmentItem(), response=response)

        # Basic identification
        loader.add_value('url', response.url)
        loader.add_value('source', 'hemnet')
        loader.add_value('scraped_at', datetime.now().isoformat())

        # Extract Hemnet ID from URL
        hemnet_id = self._extract_hemnet_id(response.url)
        if hemnet_id:
            loader.add_value('hemnet_id', hemnet_id)

        # Address - try multiple selectors
        address_selectors = [
            'h1.property-address::text',
            '.property-header h1::text',
            '[data-testid="property-address"]::text',
            '.address::text'
        ]
        for selector in address_selectors:
            address = response.css(selector).get()
            if address:
                loader.add_value('address', address.strip())
                break

        # Price - try multiple selectors
        price_selectors = [
            '.property-info__price::text',
            '[data-testid="property-price"]::text',
            '.price::text',
            '.property-price::text'
        ]
        for selector in price_selectors:
            price = response.css(selector).get()
            if price:
                loader.add_value('price', price)
                break

        # Fee (monthly fee) - try multiple selectors
        fee_selectors = [
            '.property-info__fee::text',
            '[data-testid="property-fee"]::text',
            '.fee::text',
            '.monthly-fee::text'
        ]
        for selector in fee_selectors:
            fee = response.css(selector).get()
            if fee:
                loader.add_value('fee', fee)
                break

        # Price per m2
        price_per_m2_selectors = [
            '.property-info__price-per-m2::text',
            '[data-testid="price-per-square-meter"]::text',
            '.price-per-m2::text'
        ]
        for selector in price_per_m2_selectors:
            price_per_m2 = response.css(selector).get()
            if price_per_m2:
                loader.add_value('price_per_m2', price_per_m2)
                break

        # Rooms
        rooms_selectors = [
            '.property-info__rooms::text',
            '[data-testid="property-rooms"]::text',
            '.rooms::text'
        ]
        for selector in rooms_selectors:
            rooms = response.css(selector).get()
            if rooms:
                loader.add_value('rooms', rooms)
                break

        # Year built
        year_built_selectors = [
            '.property-info__year-built::text',
            '[data-testid="construction-year"]::text',
            '.year-built::text'
        ]
        for selector in year_built_selectors:
            year_built = response.css(selector).get()
            if year_built:
                loader.add_value('year_built', year_built)
                break

        # Housing cooperative
        coop_selectors = [
            '.property-info__association::text',
            '[data-testid="housing-cooperative"]::text',
            '.housing-cooperative::text',
            '.association::text'
        ]
        for selector in coop_selectors:
            coop = response.css(selector).get()
            if coop:
                loader.add_value('housing_cooperative', coop)
                break

        # Elevator - look for text indicating elevator presence
        elevator_text = ' '.join(response.css('*::text').getall()).lower()
        has_elevator = any(keyword in elevator_text for keyword in
                          ['hiss', 'elevator', 'lift'])
        loader.add_value('has_elevator', has_elevator)

        # Balcony/Patio - look for text indicating balcony/patio presence
        balcony_text = ' '.join(response.css('*::text').getall()).lower()
        has_balcony = any(keyword in balcony_text for keyword in
                         ['balkong', 'balcony', 'terrass', 'terrace', 'uteplats', 'patio'])
        loader.add_value('has_balcony', has_balcony)

        # Floor and total floors
        floor_selectors = [
            '.property-info__floor::text',
            '[data-testid="floor"]::text',
            '.floor::text'
        ]
        for selector in floor_selectors:
            floor_info = response.css(selector).get()
            if floor_info:
                # Extract floor number and total floors from text like "3 av 5"
                floor_parts = floor_info.strip().split()
                if len(floor_parts) >= 1:
                    loader.add_value('floor', floor_parts[0])
                if len(floor_parts) >= 3:
                    loader.add_value('total_floors', floor_parts[2])
                break

        # Listing type (specific to Hemnet)
        listing_type_selectors = [
            '.property-info__type::text',
            '[data-testid="property-type"]::text',
            '.property-type::text'
        ]
        for selector in listing_type_selectors:
            listing_type = response.css(selector).get()
            if listing_type:
                loader.add_value('listing_type', listing_type)
                break

        yield loader.load_item()

    def _extract_hemnet_id(self, url):
        """Extract Hemnet ID from URL."""
        try:
            # Hemnet URLs typically look like: https://www.hemnet.se/bostad/lagenhet-3rum-sodermalm-stockholm-16012345
            # The ID is usually at the end
            parts = url.rstrip('/').split('-')
            for part in reversed(parts):
                if part.isdigit():
                    return part
        except Exception as e:
            self.logger.warning(f'Could not extract Hemnet ID from URL {url}: {e}')
        return None

