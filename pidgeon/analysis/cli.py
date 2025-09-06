"""
Command line interface for apartment analysis.

This module provides a CLI for running apartment analysis tasks.
"""

import argparse
import logging
import sys
from pathlib import Path
from pidgeon.analysis.analyzer import ApartmentAnalyzer, ScoringWeights, ScoringPreferences


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def analyze_command(args):
    """Run apartment analysis."""
    setup_logging(args.verbose)

    # Initialize analyzer with custom weights if provided
    weights = ScoringWeights()
    preferences = ScoringPreferences()

    # Override preferences if provided
    if args.max_price:
        preferences.max_preferred_price = args.max_price
    if args.max_fee:
        preferences.max_preferred_fee = args.max_fee
    if args.min_rooms:
        preferences.min_preferred_rooms = args.min_rooms
    if args.max_rooms:
        preferences.max_preferred_rooms = args.max_rooms

    analyzer = ApartmentAnalyzer(weights=weights, preferences=preferences)

    # Load and analyze data
    try:
        df = analyzer.load_data(args.input_file)
        df_analyzed = analyzer.analyze_apartments(df)

        # Export results
        output_path = args.output_file or f"analyzed_{Path(args.input_file).stem}.csv"
        analyzer.export_results(df_analyzed, output_path)

        # Generate summary report
        summary = analyzer.generate_summary_report(df_analyzed)

        print(f"\n=== ANALYSIS SUMMARY ===")
        print(f"Total apartments analyzed: {summary['total_apartments']}")
        print(f"Average score: {summary['average_score']:.3f}")
        print(f"Top 10% threshold: {summary['top_10_percent_threshold']:.3f}")
        print(f"Price range: {summary['price_stats']['min']:,.0f} - {summary['price_stats']['max']:,.0f} SEK")
        print(f"Average price: {summary['price_stats']['mean']:,.0f} SEK")
        print(f"Apartments with elevator: {summary['has_elevator_count']}")
        print(f"Apartments with balcony: {summary['has_balcony_count']}")

        print(f"\nTop 5 apartments:")
        top_5 = df_analyzed.head(5)[['rank', 'score', 'address', 'price', 'rooms']]
        for _, apt in top_5.iterrows():
            print(f"  {apt['rank']:2d}. {apt['address'][:50]:<50} | Score: {apt['score']:.3f} | {apt['price']:,.0f} SEK | {apt['rooms']} rooms")

        print(f"\nResults exported to: {output_path}")

    except Exception as e:
        logging.error(f"Analysis failed: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Pidgeon Apartment Analyzer - Analyze and score apartment listings"
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze apartment data')
    analyze_parser.add_argument('input_file', help='Path to input CSV file')
    analyze_parser.add_argument('-o', '--output-file', help='Output CSV file path')
    analyze_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose logging')

    # Scoring preferences
    scoring_group = analyze_parser.add_argument_group('scoring preferences')
    scoring_group.add_argument('--max-price', type=int, help='Maximum preferred price (SEK)')
    scoring_group.add_argument('--max-fee', type=int, help='Maximum preferred monthly fee (SEK)')
    scoring_group.add_argument('--min-rooms', type=float, help='Minimum preferred rooms')
    scoring_group.add_argument('--max-rooms', type=float, help='Maximum preferred rooms')

    analyze_parser.set_defaults(func=analyze_command)

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Run command
    args.func(args)


if __name__ == '__main__':
    main()

