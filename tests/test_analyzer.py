"""
Unit tests for the apartment analyzer business logic.
"""
import unittest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

from pidgeon.analysis.analyzer import ApartmentAnalyzer


class TestApartmentAnalyzer(unittest.TestCase):
    """Test cases for ApartmentAnalyzer class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.analyzer = ApartmentAnalyzer()

        # Sample apartment data for testing
        self.sample_data = pd.DataFrame({
            'address': ['Test St 1', 'Main Ave 2', 'Park Rd 3'],
            'price': [3000000, 4000000, 2500000],
            'fee': [3000, 4500, 2800],
            'price_per_m2': [50000, 60000, 45000],
            'rooms': [2, 3, 1],
            'living_area': [60, 67, 55],
            'year_built': [1995, 2010, 1980],
            'floor': [2, 4, 1],
            'total_floors': [5, 8, 3],
            'has_elevator': [True, True, False],
            'has_balcony': [True, False, True],
            'metro_distance': [500, 800, 300],
            'bus_distance': [100, 200, 150],
            'url': ['http://test1.com', 'http://test2.com', 'http://test3.com']
        })

    def test_analyzer_initialization(self):
        """Test that analyzer initializes with default weights."""
        self.assertIsInstance(self.analyzer.weights, dict)
        self.assertIn('price_weight', self.analyzer.weights)
        self.assertIn('location_weight', self.analyzer.weights)
        self.assertIn('size_weight', self.analyzer.weights)

    def test_custom_weights_initialization(self):
        """Test analyzer initialization with custom weights."""
        custom_weights = {
            'price_weight': 0.5,
            'location_weight': 0.3,
            'size_weight': 0.2
        }
        analyzer = ApartmentAnalyzer(weights=custom_weights)
        self.assertEqual(analyzer.weights['price_weight'], 0.5)
        self.assertEqual(analyzer.weights['location_weight'], 0.3)
        self.assertEqual(analyzer.weights['size_weight'], 0.2)

    def test_calculate_price_score(self):
        """Test price score calculation."""
        # Price score should be inversely related to price
        # (lower price = higher score)
        scores = self.analyzer._calculate_price_score(self.sample_data)

        # Check that scores are between 0 and 1
        self.assertTrue(all(0 <= score <= 1 for score in scores))

        # Check that cheaper apartments get higher scores
        cheapest_idx = self.sample_data['price'].idxmin()
        most_expensive_idx = self.sample_data['price'].idxmax()
        self.assertGreater(scores[cheapest_idx], scores[most_expensive_idx])

    def test_calculate_location_score(self):
        """Test location score calculation."""
        scores = self.analyzer._calculate_location_score(self.sample_data)

        # Check that scores are between 0 and 1
        self.assertTrue(all(0 <= score <= 1 for score in scores))

        # Check that closer to transport gets higher scores
        closest_metro_idx = self.sample_data['metro_distance'].idxmin()
        farthest_metro_idx = self.sample_data['metro_distance'].idxmax()
        self.assertGreaterEqual(scores[closest_metro_idx], scores[farthest_metro_idx])

    def test_calculate_size_score(self):
        """Test size score calculation."""
        scores = self.analyzer._calculate_size_score(self.sample_data)

        # Check that scores are between 0 and 1
        self.assertTrue(all(0 <= score <= 1 for score in scores))

        # Check that larger apartments get higher scores
        largest_idx = self.sample_data['living_area'].idxmax()
        smallest_idx = self.sample_data['living_area'].idxmin()
        self.assertGreater(scores[largest_idx], scores[smallest_idx])

    def test_calculate_amenity_score(self):
        """Test amenity score calculation."""
        scores = self.analyzer._calculate_amenity_score(self.sample_data)

        # Check that scores are between 0 and 1
        self.assertTrue(all(0 <= score <= 1 for score in scores))

        # Check that apartments with more amenities get higher scores
        # (elevator + balcony should score higher than no amenities)
        with_both_amenities = (self.sample_data['has_elevator'] &
                              self.sample_data['has_balcony'])
        with_no_amenities = (~self.sample_data['has_elevator'] &
                            ~self.sample_data['has_balcony'])

        if with_both_amenities.any() and with_no_amenities.any():
            high_amenity_idx = with_both_amenities.idxmax()
            low_amenity_idx = with_no_amenities.idxmax()
            self.assertGreater(scores[high_amenity_idx], scores[low_amenity_idx])

    def test_calculate_overall_score(self):
        """Test overall score calculation."""
        result_df = self.analyzer.calculate_scores(self.sample_data)

        # Check that overall_score column exists
        self.assertIn('overall_score', result_df.columns)

        # Check that scores are between 0 and 1
        scores = result_df['overall_score']
        self.assertTrue(all(0 <= score <= 1 for score in scores))

        # Check that all original columns are preserved
        for col in self.sample_data.columns:
            self.assertIn(col, result_df.columns)

    def test_filter_by_price(self):
        """Test filtering by price range."""
        max_price = 3500000
        filtered_df = self.analyzer.filter_apartments(
            self.sample_data,
            max_price=max_price
        )

        # Check that all apartments are within price range
        self.assertTrue(all(filtered_df['price'] <= max_price))

        # Check that expensive apartments are filtered out
        expensive_count = len(self.sample_data[self.sample_data['price'] > max_price])
        if expensive_count > 0:
            self.assertLess(len(filtered_df), len(self.sample_data))

    def test_filter_by_rooms(self):
        """Test filtering by number of rooms."""
        min_rooms = 2
        max_rooms = 2
        filtered_df = self.analyzer.filter_apartments(
            self.sample_data,
            min_rooms=min_rooms,
            max_rooms=max_rooms
        )

        # Check that all apartments have correct number of rooms
        self.assertTrue(all(filtered_df['rooms'] >= min_rooms))
        self.assertTrue(all(filtered_df['rooms'] <= max_rooms))

    def test_filter_by_fee(self):
        """Test filtering by monthly fee."""
        max_fee = 3500
        filtered_df = self.analyzer.filter_apartments(
            self.sample_data,
            max_fee=max_fee
        )

        # Check that all apartments are within fee range
        self.assertTrue(all(filtered_df['fee'] <= max_fee))

    def test_sort_by_score(self):
        """Test sorting apartments by overall score."""
        result_df = self.analyzer.calculate_scores(self.sample_data)
        sorted_df = self.analyzer.sort_apartments(result_df)

        # Check that apartments are sorted by score (descending)
        scores = sorted_df['overall_score'].values
        self.assertTrue(all(scores[i] >= scores[i+1] for i in range(len(scores)-1)))

    def test_analyze_apartments_complete_workflow(self):
        """Test the complete analysis workflow."""
        result_df = self.analyzer.analyze_apartments(
            self.sample_data,
            max_price=3500000,
            min_rooms=1,
            max_rooms=3
        )

        # Check that result has all required columns
        expected_columns = ['overall_score', 'price_score', 'location_score',
                           'size_score', 'amenity_score']
        for col in expected_columns:
            self.assertIn(col, result_df.columns)

        # Check that filtering worked
        self.assertTrue(all(result_df['price'] <= 3500000))
        self.assertTrue(all(result_df['rooms'] >= 1))
        self.assertTrue(all(result_df['rooms'] <= 3))

        # Check that sorting worked (scores in descending order)
        scores = result_df['overall_score'].values
        self.assertTrue(all(scores[i] >= scores[i+1] for i in range(len(scores)-1)))

    def test_handle_missing_data(self):
        """Test handling of missing data."""
        # Create data with missing values
        data_with_na = self.sample_data.copy()
        data_with_na.loc[0, 'metro_distance'] = np.nan
        data_with_na.loc[1, 'has_elevator'] = np.nan

        # Should not raise an exception
        result_df = self.analyzer.analyze_apartments(data_with_na)

        # Check that we get a valid result
        self.assertIsInstance(result_df, pd.DataFrame)
        self.assertIn('overall_score', result_df.columns)

    def test_empty_dataframe(self):
        """Test handling of empty dataframe."""
        empty_df = pd.DataFrame()

        # Should handle empty dataframe gracefully
        result_df = self.analyzer.analyze_apartments(empty_df)
        self.assertTrue(result_df.empty)

    def test_invalid_weights_sum(self):
        """Test that weights are normalized if they don't sum to 1."""
        weights = {
            'price_weight': 0.8,
            'location_weight': 0.6,
            'size_weight': 0.4,
            'amenity_weight': 0.2
        }
        analyzer = ApartmentAnalyzer(weights=weights)

        # Weights should be normalized to sum to 1
        total_weight = sum(analyzer.weights.values())
        self.assertAlmostEqual(total_weight, 1.0, places=5)


if __name__ == '__main__':
    unittest.main()

