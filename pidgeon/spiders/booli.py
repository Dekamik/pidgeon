"""
Booli spider for scraping apartment listings from booli.se.

This spider handles:
1. Searching through result pages
2. Extracting apartment listing URLs
3. Following links to detail pages
4. Extracting apartment data according to defined KPIs
"""

import scrapy
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs
from pidgeon.items import ApartmentItemLoader, BooliApartmentItem


class BooliSpider(scrapy.Spider):
    name = 'booli'
    allowed_domains = ['booli.se']

    # Default search URLs - can be overridden via spider arguments
    start_urls = [
        'https://www.booli.se/slutpriser/stockholm/',  # Stockholm sold apartments
    ]

    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5,
        'CONCURRENT_REQUESTS': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, search_url=None, *args, **kwargs):
        super(BooliSpider, self).__init__(*args, **kwargs)
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
            listing_urls = response.css('.search-list-item a::attr(href)').getall()

        for listing_url in listing_urls:
            absolute_url = urljoin(response.url, listing_url)
            yield response.follow(
                absolute_url,
                callback=self.parse_apartment,
                meta={'search_url': response.url}
            )

        # Follow pagination links
        next_page = response.css('a.next::attr(href)').get()
        if next_page:
            yield response.follow(
                next_page,
                callback=self.parse,
                meta={'search_url': response.url}
            )
        else:
            # Try alternative pagination selector
            next_page = response.css('.pagination .next-page::attr(href)').get()
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

        loader = ApartmentItemLoader(item=BooliApartmentItem(), response=response)

        # Basic identification
        loader.add_value('url', response.url)
        loader.add_value('source', 'booli')
        loader.add_value('scraped_at', datetime.now().isoformat())

        # Extract Booli ID from URL
        booli_id = self._extract_booli_id(response.url)
        if booli_id:
            loader.add_value('booli_id', booli_id)

        # Address - try multiple selectors
        address_selectors = [
            'h1.property-title::text',
            '.property-header h1::text',
            '[data-testid="property-address"]::text',
            '.address h1::text',
            '.listing-address::text'
        ]
        for selector in address_selectors:
            address = response.css(selector).get()
            if address:
                loader.add_value('address', address.strip())
                break

        # Price - try multiple selectors
        price_selectors = [
            '.property-price .price::text',
            '[data-testid="property-price"]::text',
            '.sold-price::text',
            '.listing-price::text',
            '.final-price::text'
        ]
        for selector in price_selectors:
            price = response.css(selector).get()
            if price:
                loader.add_value('price', price)
                break

        # Fee (monthly fee) - try multiple selectors
        fee_selectors = [
            '.property-fee::text',
            '[data-testid="monthly-fee"]::text',
            '.monthly-fee::text',
            '.avgift::text'
        ]
        for selector in fee_selectors:
            fee = response.css(selector).get()
            if fee:
                loader.add_value('fee', fee)
                break

        # Price per m2
        price_per_m2_selectors = [
            '.price-per-m2::text',
            '[data-testid="price-per-square-meter"]::text',
            '.square-meter-price::text'
        ]
        for selector in price_per_m2_selectors:
            price_per_m2 = response.css(selector).get()
            if price_per_m2:
                loader.add_value('price_per_m2', price_per_m2)
                break

        # Rooms
        rooms_selectors = [
            '.property-rooms::text',
            '[data-testid="rooms"]::text',
            '.rooms::text',
            '.antal-rum::text'
        ]
        for selector in rooms_selectors:
            rooms = response.css(selector).get()
            if rooms:
                loader.add_value('rooms', rooms)
                break

        # Year built
        year_built_selectors = [
            '.construction-year::text',
            '[data-testid="construction-year"]::text',
            '.year-built::text',
            '.byggår::text'
        ]
        for selector in year_built_selectors:
            year_built = response.css(selector).get()
            if year_built:
                loader.add_value('year_built', year_built)
                break

        # Housing cooperative
        coop_selectors = [
            '.housing-association::text',
            '[data-testid="housing-cooperative"]::text',
            '.cooperative::text',
            '.förening::text'
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
            '.floor-info::text',
            '[data-testid="floor"]::text',
            '.våning::text',
            '.floor::text'
        ]
        for selector in floor_selectors:
            floor_info = response.css(selector).get()
            if floor_info:
                # Extract floor number and total floors from text like "3 av 5" or "3/5"
                floor_parts = floor_info.strip().replace('/', ' av ').split()
                if len(floor_parts) >= 1:
                    loader.add_value('floor', floor_parts[0])
                if len(floor_parts) >= 3:
                    loader.add_value('total_floors', floor_parts[2])
                break

        # Listing status (specific to Booli)
        status_selectors = [
            '.listing-status::text',
            '[data-testid="listing-status"]::text',
            '.status::text'
        ]
        for selector in status_selectors:
            status = response.css(selector).get()
            if status:
                loader.add_value('listing_status', status)
                break

        # Extract additional metadata from structured data if available
        self._extract_structured_data(response, loader)

        yield loader.load_item()

    def _extract_booli_id(self, url):
        """Extract Booli ID from URL."""
        try:
            # Booli URLs typically look like: https://www.booli.se/bostad/lagenhet-stockholm-1234567
            # The ID is usually at the end
            parts = url.rstrip('/').split('-')
            for part in reversed(parts):
                if part.isdigit():
                    return part
        except Exception as e:
            self.logger.warning(f'Could not extract Booli ID from URL {url}: {e}')
        return None

    def _extract_structured_data(self, response, loader):
        """
        Extract data from JSON-LD structured data if available.
        Booli often includes structured data in their pages.
        """
        try:
            # Look for JSON-LD structured data
            json_ld_scripts = response.css('script[type="application/ld+json"]::text').getall()

            for script in json_ld_scripts:
                import json
                try:
                    data = json.loads(script)
                    if isinstance(data, dict):
                        # Extract relevant fields if they exist
                        if 'name' in data and not loader.get_output_value('address'):
                            loader.add_value('address', data['name'])

                        if 'offers' in data and isinstance(data['offers'], dict):
                            offers = data['offers']
                            if 'price' in offers and not loader.get_output_value('price'):
                                loader.add_value('price', offers['price'])

                        # Look for property-specific data
                        if '@type' in data and 'RealEstate' in str(data['@type']):
                            if 'floorSize' in data:
                                # Could be used to calculate price per m2 if not available
                                pass
                            if 'numberOfRooms' in data and not loader.get_output_value('rooms'):
                                loader.add_value('rooms', data['numberOfRooms'])

                except json.JSONDecodeError:
                    continue

        except Exception as e:
            self.logger.debug(f'Could not extract structured data: {e}')

