"""
Apartment analyzer for scoring and sorting apartment listings based on KPIs.

This module provides functionality to:
1. Load apartment data from CSV files
2. Apply weighted scoring based on configurable criteria
3. Sort apartments by their calculated scores
4. Export results to CSV
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import logging


@dataclass
class ScoringWeights:
    """
    Configuration class for apartment scoring weights.

    Each weight represents the importance of a specific KPI.
    Higher weights mean the factor has more impact on the final score.
    """
    # Financial factors (higher is better for lower values)
    price_weight: float = 0.3
    fee_weight: float = 0.2
    price_per_m2_weight: float = 0.25

    # Property characteristics (higher is better for higher values)
    rooms_weight: float = 0.1
    year_built_weight: float = 0.1

    # Building features (boolean - presence adds to score)
    elevator_weight: float = 0.03
    balcony_weight: float = 0.02

    # Floor preferences (customizable)
    floor_weight: float = 0.0  # Can be adjusted based on preferences

    def __post_init__(self):
        """Validate that weights sum to approximately 1.0."""
        total = (self.price_weight + self.fee_weight + self.price_per_m2_weight +
                self.rooms_weight + self.year_built_weight + self.elevator_weight +
                self.balcony_weight + self.floor_weight)

        if not (0.95 <= total <= 1.05):
            logging.warning(f"Scoring weights sum to {total:.3f}, not close to 1.0")


@dataclass
class ScoringPreferences:
    """
    Configuration class for apartment scoring preferences.

    These define what constitutes "good" or "bad" values for scoring.
    """
    # Price preferences (in SEK)
    max_preferred_price: int = 4000000  # 4M SEK
    min_acceptable_price: int = 1000000  # 1M SEK

    # Fee preferences (in SEK per month)
    max_preferred_fee: int = 5000
    min_acceptable_fee: int = 2000

    # Price per m2 preferences (in SEK per m2)
    max_preferred_price_per_m2: int = 70000
    min_acceptable_price_per_m2: int = 30000

    # Property preferences
    min_preferred_rooms: float = 2.0
    max_preferred_rooms: float = 4.0
    min_preferred_year: int = 1960
    preferred_year_threshold: int = 1990

    # Floor preferences (None means no preference)
    preferred_min_floor: Optional[int] = 2
    preferred_max_floor: Optional[int] = 6
    avoid_ground_floor: bool = True


class ApartmentAnalyzer:
    """
    Main analyzer class for apartment data processing and scoring.
    """

    def __init__(self,
                 weights: Optional[ScoringWeights] = None,
                 preferences: Optional[ScoringPreferences] = None):
        """
        Initialize the analyzer with scoring configuration.

        Args:
            weights: Scoring weights configuration
            preferences: Scoring preferences configuration
        """
        self.weights = weights or ScoringWeights()
        self.preferences = preferences or ScoringPreferences()
        self.logger = logging.getLogger(__name__)

    def load_data(self, file_path: str) -> pd.DataFrame:
        """
        Load apartment data from CSV file.

        Args:
            file_path: Path to the CSV file

        Returns:
            DataFrame with apartment data
        """
        try:
            df = pd.read_csv(file_path)
            self.logger.info(f"Loaded {len(df)} apartments from {file_path}")
            return df
        except Exception as e:
            self.logger.error(f"Error loading data from {file_path}: {e}")
            raise

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and prepare apartment data for analysis.

        Args:
            df: Raw apartment data

        Returns:
            Cleaned DataFrame
        """
        df_clean = df.copy()

        # Convert boolean columns
        for col in ['has_elevator', 'has_balcony']:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].map({
                    'Yes': True, 'No': False, 'yes': True, 'no': False,
                    True: True, False: False, 1: True, 0: False
                }).fillna(False)

        # Convert numeric columns
        numeric_cols = ['price', 'fee', 'price_per_m2', 'rooms', 'year_built', 'floor', 'total_floors']
        for col in numeric_cols:
            if col in df_clean.columns:
                # Remove non-numeric characters and convert
                df_clean[col] = pd.to_numeric(
                    df_clean[col].astype(str).str.replace(r'[^\d.]', '', regex=True),
                    errors='coerce'
                )

        # Log data quality
        self.logger.info(f"Data cleaning complete. Shape: {df_clean.shape}")
        for col in numeric_cols:
            if col in df_clean.columns:
                missing = df_clean[col].isna().sum()
                if missing > 0:
                    self.logger.warning(f"Missing values in {col}: {missing}")

        return df_clean

    def score_price(self, price: float) -> float:
        """Score apartment based on price (lower is better)."""
        if pd.isna(price):
            return 0.0

        if price <= self.preferences.max_preferred_price:
            # Linear scale: max score for min price, decreasing as price increases
            score = 1.0 - (price - self.preferences.min_acceptable_price) / \
                    (self.preferences.max_preferred_price - self.preferences.min_acceptable_price)
            return max(0.0, min(1.0, score))
        else:
            # Exponential decay for prices above preferred max
            decay_factor = (price - self.preferences.max_preferred_price) / self.preferences.max_preferred_price
            return max(0.0, 0.3 * np.exp(-decay_factor))

    def score_fee(self, fee: float) -> float:
        """Score apartment based on monthly fee (lower is better)."""
        if pd.isna(fee):
            return 0.5  # Neutral score for missing fee data

        if fee <= self.preferences.max_preferred_fee:
            score = 1.0 - (fee - self.preferences.min_acceptable_fee) / \
                    (self.preferences.max_preferred_fee - self.preferences.min_acceptable_fee)
            return max(0.0, min(1.0, score))
        else:
            decay_factor = (fee - self.preferences.max_preferred_fee) / self.preferences.max_preferred_fee
            return max(0.0, 0.3 * np.exp(-decay_factor))

    def score_price_per_m2(self, price_per_m2: float) -> float:
        """Score apartment based on price per square meter (lower is better)."""
        if pd.isna(price_per_m2):
            return 0.5  # Neutral score for missing data

        if price_per_m2 <= self.preferences.max_preferred_price_per_m2:
            score = 1.0 - (price_per_m2 - self.preferences.min_acceptable_price_per_m2) / \
                    (self.preferences.max_preferred_price_per_m2 - self.preferences.min_acceptable_price_per_m2)
            return max(0.0, min(1.0, score))
        else:
            decay_factor = (price_per_m2 - self.preferences.max_preferred_price_per_m2) / \
                          self.preferences.max_preferred_price_per_m2
            return max(0.0, 0.2 * np.exp(-decay_factor))

    def score_rooms(self, rooms: float) -> float:
        """Score apartment based on number of rooms."""
        if pd.isna(rooms):
            return 0.5

        if self.preferences.min_preferred_rooms <= rooms <= self.preferences.max_preferred_rooms:
            return 1.0
        elif rooms < self.preferences.min_preferred_rooms:
            # Penalty for too few rooms
            return max(0.0, rooms / self.preferences.min_preferred_rooms)
        else:
            # Diminishing returns for too many rooms
            excess = rooms - self.preferences.max_preferred_rooms
            return max(0.1, 1.0 - 0.1 * excess)

    def score_year_built(self, year_built: float) -> float:
        """Score apartment based on construction year (newer is generally better)."""
        if pd.isna(year_built):
            return 0.5

        if year_built >= self.preferences.preferred_year_threshold:
            return 1.0
        elif year_built >= self.preferences.min_preferred_year:
            # Linear scale between min and preferred year
            score = (year_built - self.preferences.min_preferred_year) / \
                   (self.preferences.preferred_year_threshold - self.preferences.min_preferred_year)
            return max(0.1, score)
        else:
            # Very old buildings get low score
            return 0.1

    def score_floor(self, floor: float, total_floors: float) -> float:
        """Score apartment based on floor preferences."""
        if pd.isna(floor):
            return 0.5

        # Avoid ground floor if preference is set
        if self.preferences.avoid_ground_floor and floor <= 1:
            return 0.2

        # Apply floor preferences if set
        if self.preferences.preferred_min_floor and self.preferences.preferred_max_floor:
            if self.preferences.preferred_min_floor <= floor <= self.preferences.preferred_max_floor:
                return 1.0
            elif floor < self.preferences.preferred_min_floor:
                return 0.6
            else:
                return 0.7

        return 0.8  # Neutral score if no specific preferences

    def calculate_apartment_score(self, apartment: pd.Series) -> float:
        """
        Calculate overall score for a single apartment.

        Args:
            apartment: Series containing apartment data

        Returns:
            Calculated score between 0 and 1
        """
        score = 0.0

        # Financial factors
        score += self.weights.price_weight * self.score_price(apartment.get('price'))
        score += self.weights.fee_weight * self.score_fee(apartment.get('fee'))
        score += self.weights.price_per_m2_weight * self.score_price_per_m2(apartment.get('price_per_m2'))

        # Property characteristics
        score += self.weights.rooms_weight * self.score_rooms(apartment.get('rooms'))
        score += self.weights.year_built_weight * self.score_year_built(apartment.get('year_built'))
        score += self.weights.floor_weight * self.score_floor(apartment.get('floor'), apartment.get('total_floors'))

        # Building features (binary bonuses)
        if apartment.get('has_elevator', False):
            score += self.weights.elevator_weight
        if apartment.get('has_balcony', False):
            score += self.weights.balcony_weight

        return min(1.0, score)  # Cap at 1.0

    def analyze_apartments(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Analyze and score all apartments in the DataFrame.

        Args:
            df: DataFrame with apartment data

        Returns:
            DataFrame with added score column, sorted by score descending
        """
        # Clean the data
        df_clean = self.clean_data(df)

        # Calculate scores
        self.logger.info("Calculating apartment scores...")
        df_clean['score'] = df_clean.apply(self.calculate_apartment_score, axis=1)

        # Sort by score (highest first)
        df_scored = df_clean.sort_values('score', ascending=False).reset_index(drop=True)

        # Add ranking
        df_scored['rank'] = range(1, len(df_scored) + 1)

        self.logger.info(f"Analysis complete. Best score: {df_scored['score'].max():.3f}")
        self.logger.info(f"Worst score: {df_scored['score'].min():.3f}")
        self.logger.info(f"Average score: {df_scored['score'].mean():.3f}")

        return df_scored

    def export_results(self, df: pd.DataFrame, output_path: str) -> None:
        """
        Export analyzed results to CSV.

        Args:
            df: DataFrame with analyzed apartment data
            output_path: Path for output CSV file
        """
        try:
            # Reorder columns to put score and rank first
            cols = ['rank', 'score', 'address', 'price', 'fee', 'price_per_m2', 'rooms', 'year_built']
            remaining_cols = [col for col in df.columns if col not in cols]
            df_export = df[cols + remaining_cols]

            df_export.to_csv(output_path, index=False)
            self.logger.info(f"Results exported to {output_path}")
        except Exception as e:
            self.logger.error(f"Error exporting results: {e}")
            raise

    def generate_summary_report(self, df: pd.DataFrame) -> Dict:
        """
        Generate a summary report of the analysis.

        Args:
            df: Analyzed apartment DataFrame

        Returns:
            Dictionary with summary statistics
        """
        summary = {
            'total_apartments': len(df),
            'average_score': df['score'].mean(),
            'score_std': df['score'].std(),
            'top_10_percent_threshold': df['score'].quantile(0.9),
            'price_stats': {
                'mean': df['price'].mean(),
                'median': df['price'].median(),
                'min': df['price'].min(),
                'max': df['price'].max()
            },
            'rooms_distribution': df['rooms'].value_counts().to_dict(),
            'has_elevator_count': df['has_elevator'].sum() if 'has_elevator' in df.columns else 0,
            'has_balcony_count': df['has_balcony'].sum() if 'has_balcony' in df.columns else 0,
        }

        return summary

