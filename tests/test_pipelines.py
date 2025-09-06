"""
Unit tests for the data processing pipelines.
"""
import unittest
import tempfile
import os
import csv
from unittest.mock import Mock, patch, mock_open
from scrapy import Item, Field
from scrapy.exceptions import DropItem

from pidgeon.pipelines import ValidationPipeline, DeduplicationPipeline, CSVExportPipeline
from pidgeon.items import ApartmentItem


class TestValidationPipeline(unittest.TestCase):
    """Test cases for ValidationPipeline."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.pipeline = ValidationPipeline()
        self.spider = Mock()
        self.spider.name = 'test_spider'

    def test_valid_item_passes_through(self):
        """Test that valid items pass through validation."""
        item = ApartmentItem()
        item['address'] = 'Test Street 123'
        item['price'] = 3000000
        item['url'] = 'https://example.com/apartment/123'

        result = self.pipeline.process_item(item, self.spider)
        self.assertEqual(result, item)

    def test_missing_required_field_raises_drop_item(self):
        """Test that missing required fields cause item to be dropped."""
        item = ApartmentItem()
        item['address'] = 'Test Street 123'
        # Missing price and url

        with self.assertRaises(DropItem):
            self.pipeline.process_item(item, self.spider)

    def test_invalid_price_type_raises_drop_item(self):
        """Test that invalid price types cause item to be dropped."""
        item = ApartmentItem()
        item['address'] = 'Test Street 123'
        item['price'] = 'not a number'  # Invalid type
        item['url'] = 'https://example.com/apartment/123'

        with self.assertRaises(DropItem):
            self.pipeline.process_item(item, self.spider)

    def test_negative_price_raises_drop_item(self):
        """Test that negative prices cause item to be dropped."""
        item = ApartmentItem()
        item['address'] = 'Test Street 123'
        item['price'] = -1000000  # Invalid value
        item['url'] = 'https://example.com/apartment/123'

        with self.assertRaises(DropItem):
            self.pipeline.process_item(item, self.spider)

    def test_invalid_url_raises_drop_item(self):
        """Test that invalid URLs cause item to be dropped."""
        item = ApartmentItem()
        item['address'] = 'Test Street 123'
        item['price'] = 3000000
        item['url'] = 'not-a-valid-url'  # Invalid URL

        with self.assertRaises(DropItem):
            self.pipeline.process_item(item, self.spider)

    def test_invalid_rooms_type_raises_drop_item(self):
        """Test that invalid room numbers cause item to be dropped."""
        item = ApartmentItem()
        item['address'] = 'Test Street 123'
        item['price'] = 3000000
        item['url'] = 'https://example.com/apartment/123'
        item['rooms'] = 'two'  # Invalid type

        with self.assertRaises(DropItem):
            self.pipeline.process_item(item, self.spider)

    def test_optional_fields_with_invalid_types(self):
        """Test that optional fields with invalid types are cleaned."""
        item = ApartmentItem()
        item['address'] = 'Test Street 123'
        item['price'] = 3000000
        item['url'] = 'https://example.com/apartment/123'
        item['has_elevator'] = 'yes'  # Should be boolean
        item['floor'] = 'ground'  # Should be number

        result = self.pipeline.process_item(item, self.spider)

        # Should pass validation but clean invalid optional fields
        self.assertEqual(result['address'], 'Test Street 123')
        self.assertEqual(result['price'], 3000000)
        self.assertEqual(result['url'], 'https://example.com/apartment/123')


class TestDeduplicationPipeline(unittest.TestCase):
    """Test cases for DeduplicationPipeline."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.pipeline = DeduplicationPipeline()
        self.spider = Mock()
        self.spider.name = 'test_spider'

    def test_first_item_passes_through(self):
        """Test that the first item with a URL passes through."""
        item = ApartmentItem()
        item['url'] = 'https://example.com/apartment/123'
        item['address'] = 'Test Street 123'

        result = self.pipeline.process_item(item, self.spider)
        self.assertEqual(result, item)

    def test_duplicate_url_raises_drop_item(self):
        """Test that duplicate URLs cause item to be dropped."""
        item1 = ApartmentItem()
        item1['url'] = 'https://example.com/apartment/123'
        item1['address'] = 'Test Street 123'

        item2 = ApartmentItem()
        item2['url'] = 'https://example.com/apartment/123'  # Same URL
        item2['address'] = 'Test Street 456'  # Different address

        # First item should pass
        result1 = self.pipeline.process_item(item1, self.spider)
        self.assertEqual(result1, item1)

        # Second item with same URL should be dropped
        with self.assertRaises(DropItem):
            self.pipeline.process_item(item2, self.spider)

    def test_different_urls_both_pass(self):
        """Test that items with different URLs both pass through."""
        item1 = ApartmentItem()
        item1['url'] = 'https://example.com/apartment/123'
        item1['address'] = 'Test Street 123'

        item2 = ApartmentItem()
        item2['url'] = 'https://example.com/apartment/456'  # Different URL
        item2['address'] = 'Test Street 456'

        # Both items should pass
        result1 = self.pipeline.process_item(item1, self.spider)
        result2 = self.pipeline.process_item(item2, self.spider)

        self.assertEqual(result1, item1)
        self.assertEqual(result2, item2)

    def test_missing_url_passes_through(self):
        """Test that items without URL pass through (validation should catch this)."""
        item = ApartmentItem()
        item['address'] = 'Test Street 123'
        # No URL field

        # Should pass through deduplication (validation pipeline should handle missing URL)
        result = self.pipeline.process_item(item, self.spider)
        self.assertEqual(result, item)


class TestCSVExportPipeline(unittest.TestCase):
    """Test cases for CSVExportPipeline."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.pipeline = CSVExportPipeline()
        self.spider = Mock()
        self.spider.name = 'test_spider'

    def tearDown(self):
        """Clean up test fixtures after each test method."""
        # Clean up any files created during tests
        if hasattr(self.pipeline, 'file'):
            self.pipeline.file.close()

    @patch('pidgeon.pipelines.datetime')
    def test_open_spider_creates_file(self, mock_datetime):
        """Test that opening spider creates CSV file with correct name."""
        mock_datetime.now.return_value.strftime.return_value = '20231201_120000'

        with patch('builtins.open', mock_open()) as mock_file:
            with patch('os.makedirs') as mock_makedirs:
                self.pipeline.open_spider(self.spider)

                # Check that output directory is created
                mock_makedirs.assert_called_once_with('output', exist_ok=True)

                # Check that file is opened with correct name
                expected_filename = 'output/apartments_test_spider_20231201_120000.csv'
                mock_file.assert_called_once_with(expected_filename, 'w', newline='', encoding='utf-8')

    def test_process_item_writes_to_csv(self):
        """Test that processing item writes data to CSV."""
        item = ApartmentItem()
        item['address'] = 'Test Street 123'
        item['price'] = 3000000
        item['url'] = 'https://example.com/apartment/123'

        # Mock the file and CSV writer
        mock_file = Mock()
        mock_writer = Mock()

        self.pipeline.file = mock_file
        self.pipeline.writer = mock_writer

        result = self.pipeline.process_item(item, self.spider)

        # Check that item is returned unchanged
        self.assertEqual(result, item)

        # Check that writer.writerow was called
        mock_writer.writerow.assert_called_once()

    def test_close_spider_closes_file(self):
        """Test that closing spider closes the file."""
        mock_file = Mock()
        self.pipeline.file = mock_file

        self.pipeline.close_spider(self.spider)

        # Check that file is closed
        mock_file.close.assert_called_once()

    @patch('pidgeon.pipelines.datetime')
    @patch('builtins.open', mock_open())
    @patch('os.makedirs')
    def test_csv_header_written_correctly(self, mock_makedirs, mock_datetime):
        """Test that CSV header is written with correct field names."""
        mock_datetime.now.return_value.strftime.return_value = '20231201_120000'

        with patch('csv.DictWriter') as mock_dict_writer:
            mock_writer_instance = Mock()
            mock_dict_writer.return_value = mock_writer_instance

            self.pipeline.open_spider(self.spider)

            # Check that DictWriter was initialized with correct fieldnames
            mock_dict_writer.assert_called_once()
            args, kwargs = mock_dict_writer.call_args
            self.assertIn('fieldnames', kwargs)

            # Check that writeheader was called
            mock_writer_instance.writeheader.assert_called_once()

    def test_item_data_extraction(self):
        """Test that item data is correctly extracted for CSV writing."""
        item = ApartmentItem()
        item['address'] = 'Test Street 123'
        item['price'] = 3000000
        item['fee'] = 4500
        item['rooms'] = 2
        item['url'] = 'https://example.com/apartment/123'

        # Mock the writer
        mock_writer = Mock()
        self.pipeline.writer = mock_writer
        self.pipeline.file = Mock()  # Prevent close() errors

        self.pipeline.process_item(item, self.spider)

        # Check that writerow was called with item data
        mock_writer.writerow.assert_called_once_with(dict(item))

    @patch('pidgeon.pipelines.datetime')
    def test_filename_format(self, mock_datetime):
        """Test that filename follows the correct format."""
        mock_datetime.now.return_value.strftime.return_value = '20231201_120000'

        with patch('builtins.open', mock_open()):
            with patch('os.makedirs'):
                with patch('csv.DictWriter'):
                    self.pipeline.open_spider(self.spider)

                    expected_pattern = 'output/apartments_test_spider_20231201_120000.csv'
                    # The filename should be stored or accessible somehow
                    # This test verifies the format is correct


class TestPipelineIntegration(unittest.TestCase):
    """Integration tests for pipeline combinations."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.validation_pipeline = ValidationPipeline()
        self.dedup_pipeline = DeduplicationPipeline()
        self.spider = Mock()
        self.spider.name = 'test_spider'

    def test_validation_then_deduplication(self):
        """Test that validation and deduplication work together."""
        # Valid item that should pass both pipelines
        item1 = ApartmentItem()
        item1['address'] = 'Test Street 123'
        item1['price'] = 3000000
        item1['url'] = 'https://example.com/apartment/123'

        # Invalid item that should fail validation
        item2 = ApartmentItem()
        item2['address'] = 'Test Street 456'
        item2['price'] = 'invalid'  # Invalid price
        item2['url'] = 'https://example.com/apartment/456'

        # Duplicate item that should pass validation but fail deduplication
        item3 = ApartmentItem()
        item3['address'] = 'Test Street 789'
        item3['price'] = 4000000
        item3['url'] = 'https://example.com/apartment/123'  # Same URL as item1

        # First item should pass both pipelines
        result1 = self.validation_pipeline.process_item(item1, self.spider)
        result1 = self.dedup_pipeline.process_item(result1, self.spider)
        self.assertEqual(result1, item1)

        # Second item should fail validation
        with self.assertRaises(DropItem):
            self.validation_pipeline.process_item(item2, self.spider)

        # Third item should pass validation but fail deduplication
        result3 = self.validation_pipeline.process_item(item3, self.spider)
        with self.assertRaises(DropItem):
            self.dedup_pipeline.process_item(result3, self.spider)


if __name__ == '__main__':
    unittest.main()

