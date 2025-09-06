# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from itemloaders.processors import TakeFirst, MapCompose, Join
from scrapy.loader import ItemLoader


def clean_price(value):
    """Clean price strings by removing non-numeric characters except spaces and commas."""
    if value:
        # Remove currency symbols and other non-numeric characters
        import re
        cleaned = re.sub(r'[^\d\s,]', '', str(value))
        return cleaned.strip()
    return value


def clean_text(value):
    """Clean text by stripping whitespace and normalizing."""
    if value:
        return str(value).strip()
    return value


def parse_boolean(value):
    """Parse boolean values from text."""
    if value:
        value_str = str(value).lower().strip()
        return value_str in ['yes', 'ja', 'true', '1', 'finns', 'hiss']
    return False


def parse_integer(value):
    """Parse integer values from text."""
    if value:
        import re
        # Extract first number found in the string
        match = re.search(r'\d+', str(value))
        if match:
            return int(match.group())
    return None


class ApartmentItem(scrapy.Item):
    """
    Common data structure for apartment listings from different sources.

    This item defines all the KPIs we care about for apartment analysis:
    - Address
    - Price
    - Fee
    - Price per m2
    - Amount of rooms
    - Year built
    - Name of housing cooperative
    - If the building has an elevator
    - If the apartment has a balcony or patio
    - Floor
    - Total amount of floors in building
    - The URL to the detail view
    """
    # Basic identification
    url = scrapy.Field()
    source = scrapy.Field()  # 'hemnet' or 'booli'

    # Location information
    address = scrapy.Field()

    # Financial information
    price = scrapy.Field()
    fee = scrapy.Field()
    price_per_m2 = scrapy.Field()

    # Property details
    rooms = scrapy.Field()
    year_built = scrapy.Field()
    housing_cooperative = scrapy.Field()

    # Building features
    has_elevator = scrapy.Field()
    has_balcony = scrapy.Field()
    floor = scrapy.Field()
    total_floors = scrapy.Field()

    # Additional metadata
    scraped_at = scrapy.Field()


class ApartmentItemLoader(ItemLoader):
    """
    Custom ItemLoader for apartment data with appropriate processors
    for cleaning and validating the scraped data.
    """
    default_item_class = ApartmentItem
    default_output_processor = TakeFirst()

    # Text fields
    address_in = MapCompose(clean_text)
    housing_cooperative_in = MapCompose(clean_text)
    source_in = MapCompose(clean_text)

    # Numeric fields
    price_in = MapCompose(clean_price, parse_integer)
    fee_in = MapCompose(clean_price, parse_integer)
    price_per_m2_in = MapCompose(clean_price, parse_integer)
    rooms_in = MapCompose(parse_integer)
    year_built_in = MapCompose(parse_integer)
    floor_in = MapCompose(parse_integer)
    total_floors_in = MapCompose(parse_integer)

    # Boolean fields
    has_elevator_in = MapCompose(parse_boolean)
    has_balcony_in = MapCompose(parse_boolean)

    # URL field (no processing needed)
    url_in = MapCompose(clean_text)


class HemnetApartmentItem(ApartmentItem):
    """
    Hemnet-specific apartment item with additional fields that may be
    specific to Hemnet listings.
    """
    # Hemnet-specific fields can be added here if needed
    hemnet_id = scrapy.Field()
    listing_type = scrapy.Field()  # e.g., 'bostadsratt', 'villa', etc.


class BooliApartmentItem(ApartmentItem):
    """
    Booli-specific apartment item with additional fields that may be
    specific to Booli listings.
    """
    # Booli-specific fields can be added here if needed
    booli_id = scrapy.Field()
    listing_status = scrapy.Field()  # e.g., 'active', 'sold', etc.

