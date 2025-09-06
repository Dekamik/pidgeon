# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import csv
import os
from datetime import datetime
from typing import Dict, Any
from scrapy import Item
from scrapy.exceptions import DropItem
from pidgeon.items import ApartmentItem


class ValidationPipeline:
    """
    Pipeline to validate apartment items before processing.
    Ensures required fields are present and valid.
    """

    required_fields = ['url', 'source', 'address']

    def process_item(self, item: Item, spider) -> Item:
        """Validate item fields and drop invalid items."""

        # Check required fields
        for field in self.required_fields:
            if not item.get(field):
                raise DropItem(f"Missing required field: {field} in {item}")

        # Validate price is numeric if present
        if item.get('price'):
            try:
                price = int(str(item['price']).replace(' ', '').replace(',', ''))
                if price <= 0:
                    raise DropItem(f"Invalid price: {item['price']} in {item}")
            except (ValueError, TypeError):
                spider.logger.warning(f"Invalid price format: {item['price']} in {item}")
                # Don't drop item, just log warning

        # Validate fee is numeric if present
        if item.get('fee'):
            try:
                fee = int(str(item['fee']).replace(' ', '').replace(',', ''))
                if fee < 0:
                    raise DropItem(f"Invalid fee: {item['fee']} in {item}")
            except (ValueError, TypeError):
                spider.logger.warning(f"Invalid fee format: {item['fee']} in {item}")

        # Validate rooms if present
        if item.get('rooms'):
            try:
                rooms = float(item['rooms'])
                if rooms <= 0 or rooms > 20:  # Reasonable limits
                    spider.logger.warning(f"Unusual room count: {item['rooms']} in {item}")
            except (ValueError, TypeError):
                spider.logger.warning(f"Invalid room format: {item['rooms']} in {item}")

        # Validate year built if present
        if item.get('year_built'):
            try:
                year = int(item['year_built'])
                current_year = datetime.now().year
                if year < 1800 or year > current_year:
                    spider.logger.warning(f"Unusual year built: {item['year_built']} in {item}")
            except (ValueError, TypeError):
                spider.logger.warning(f"Invalid year format: {item['year_built']} in {item}")

        return item


class DuplicatesPipeline:
    """
    Pipeline to filter out duplicate apartment listings.
    Uses URL as the unique identifier.
    """

    def __init__(self):
        self.seen_urls = set()

    def process_item(self, item: Item, spider) -> Item:
        """Filter out duplicate items based on URL."""
        url = item.get('url')

        if url in self.seen_urls:
            raise DropItem(f"Duplicate item found: {url}")
        else:
            self.seen_urls.add(url)
            return item


class DataEnrichmentPipeline:
    """
    Pipeline to enrich apartment data with calculated fields.
    """

    def process_item(self, item: Item, spider) -> Item:
        """Enrich item with calculated fields."""

        # Calculate price per m2 if not already present
        if not item.get('price_per_m2') and item.get('price'):
            # This would require apartment size data
            # For now, we'll skip this calculation
            pass

        # Standardize boolean fields
        for bool_field in ['has_elevator', 'has_balcony']:
            if item.get(bool_field) is not None:
                item[bool_field] = bool(item[bool_field])

        # Ensure scraped_at timestamp
        if not item.get('scraped_at'):
            item['scraped_at'] = datetime.now().isoformat()

        return item


class CSVExportPipeline:
    """
    Pipeline to export apartment data to CSV files.
    Creates separate files for each spider run.
    """

    def __init__(self):
        self.files = {}
        self.writers = {}
        self.output_dir = 'output'

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

    def open_spider(self, spider):
        """Initialize CSV file for the spider."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.output_dir}/apartments_{spider.name}_{timestamp}.csv"

        self.files[spider] = open(filename, 'w', newline='', encoding='utf-8')

        # Define CSV columns based on ApartmentItem fields
        fieldnames = [
            'url', 'source', 'address', 'price', 'fee', 'price_per_m2',
            'rooms', 'year_built', 'housing_cooperative', 'has_elevator',
            'has_balcony', 'floor', 'total_floors', 'scraped_at'
        ]

        self.writers[spider] = csv.DictWriter(
            self.files[spider],
            fieldnames=fieldnames,
            extrasaction='ignore'
        )
        self.writers[spider].writeheader()

        spider.logger.info(f"CSV export pipeline initialized: {filename}")

    def close_spider(self, spider):
        """Close CSV file when spider finishes."""
        if spider in self.files:
            self.files[spider].close()
            del self.files[spider]
            del self.writers[spider]

    def process_item(self, item: Item, spider) -> Item:
        """Write item to CSV file."""
        if spider in self.writers:
            # Convert item to dict and handle None values
            item_dict = {}
            for key, value in item.items():
                if value is None:
                    item_dict[key] = ''
                elif isinstance(value, bool):
                    item_dict[key] = 'Yes' if value else 'No'
                else:
                    item_dict[key] = str(value)

            self.writers[spider].writerow(item_dict)
            self.files[spider].flush()  # Ensure data is written immediately

        return item


class StatisticsPipeline:
    """
    Pipeline to collect statistics about scraped data.
    """

    def __init__(self):
        self.stats = {
            'total_items': 0,
            'items_by_source': {},
            'price_stats': {'min': float('inf'), 'max': 0, 'total': 0, 'count': 0},
            'rooms_distribution': {},
        }

    def process_item(self, item: Item, spider) -> Item:
        """Collect statistics from item."""
        self.stats['total_items'] += 1

        # Count by source
        source = item.get('source', 'unknown')
        self.stats['items_by_source'][source] = self.stats['items_by_source'].get(source, 0) + 1

        # Price statistics
        if item.get('price'):
            try:
                price = int(str(item['price']).replace(' ', '').replace(',', ''))
                self.stats['price_stats']['min'] = min(self.stats['price_stats']['min'], price)
                self.stats['price_stats']['max'] = max(self.stats['price_stats']['max'], price)
                self.stats['price_stats']['total'] += price
                self.stats['price_stats']['count'] += 1
            except (ValueError, TypeError):
                pass

        # Rooms distribution
        if item.get('rooms'):
            try:
                rooms = str(item['rooms'])
                self.stats['rooms_distribution'][rooms] = self.stats['rooms_distribution'].get(rooms, 0) + 1
            except (ValueError, TypeError):
                pass

        return item

    def close_spider(self, spider):
        """Log statistics when spider finishes."""
        spider.logger.info("=== SCRAPING STATISTICS ===")
        spider.logger.info(f"Total items scraped: {self.stats['total_items']}")

        for source, count in self.stats['items_by_source'].items():
            spider.logger.info(f"Items from {source}: {count}")

        if self.stats['price_stats']['count'] > 0:
            avg_price = self.stats['price_stats']['total'] / self.stats['price_stats']['count']
            spider.logger.info(f"Price range: {self.stats['price_stats']['min']:,} - {self.stats['price_stats']['max']:,}")
            spider.logger.info(f"Average price: {avg_price:,.0f}")

        if self.stats['rooms_distribution']:
            spider.logger.info("Rooms distribution:")
            for rooms, count in sorted(self.stats['rooms_distribution'].items()):
                spider.logger.info(f"  {rooms} rooms: {count} apartments")

        spider.logger.info("===========================")

