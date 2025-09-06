# Pidgeon 🏠

An apartment marketplace scraper and analyzer for Swedish real estate websites. Pidgeon scrapes apartment listings from Hemnet.se and Booli.se, analyzes them using weighted KPIs, and outputs ranked results to CSV files.

## Features

- 🕷️ **Web Scraping**: Automated scraping of apartment listings from Hemnet and Booli
- 📊 **Smart Analysis**: Weighted scoring system based on customizable KPIs
- 🏗️ **Extensible Architecture**: Easy to add new websites and metrics
- 📈 **Data Export**: Clean CSV output with comprehensive apartment data
- 🛡️ **Rate Limiting**: Built-in delays to respect website resources
- 🧪 **Unit Tested**: Comprehensive test coverage for business logic

## Quick Start

### 1. Setup Environment

```bash
# Clone and setup the project
git clone <repository-url>
cd pidgeon

# Quick setup with all dependencies
make quickstart
```

### 2. Run Your First Scrape

```bash
# Scrape apartments from Hemnet
make scrape-hemnet

# Or scrape from Booli
make scrape-booli

# Or scrape from both sites
make scrape-all
```

### 3. Analyze Results

```bash
# Analyze the latest scraped data
make analyze-latest

# Or analyze a specific file
make analyze INPUT_FILE=output/apartments_hemnet_20231201_120000.csv
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip and venv

### Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Scraping Apartments

#### Basic Scraping

```bash
# Scrape from default Hemnet search (Stockholm area)
make scrape-hemnet

# Scrape from default Booli search
make scrape-booli
```

#### Custom Search URLs

```bash
# Scrape specific Hemnet search results
make scrape-hemnet-url URL='https://www.hemnet.se/bostader?location_ids%5B%5D=17744&item_types%5B%5D=bostadsratt'

# Scrape specific Booli search results
make scrape-booli-url URL='https://www.booli.se/slutpriser/stockholm/2-rum/'
```

#### Using Scrapy Directly

```bash
# Activate virtual environment first
source venv/bin/activate

# Run spiders directly with Scrapy
scrapy crawl hemnet
scrapy crawl booli

# Run with custom parameters
scrapy crawl hemnet -a search_url='https://www.hemnet.se/...'
```

### Data Analysis

#### Quick Analysis

```bash
# Analyze most recent scraped data
make analyze-latest
```

#### Custom Analysis Parameters

```bash
# Analyze with custom filters
make analyze-custom INPUT_FILE=output/apartments_hemnet_20231201_120000.csv \
    MAX_PRICE=4000000 \
    MAX_FEE=5000 \
    MIN_ROOMS=2 \
    MAX_ROOMS=4
```

#### Python Analysis Module

```bash
# Activate virtual environment
source venv/bin/activate

# Use the analysis CLI directly
python -m pidgeon.analysis.cli analyze output/apartments_hemnet_20231201_120000.csv

# With custom filters
python -m pidgeon.analysis.cli analyze output/apartments_hemnet_20231201_120000.csv \
    --max-price 4000000 \
    --max-fee 5000 \
    --min-rooms 2 \
    --max-rooms 4
```

### Output Files

Scraped data is saved to the `output/` directory with timestamped filenames:

```
output/
├── apartments_hemnet_20231201_120000.csv
├── apartments_booli_20231201_130000.csv
└── analysis_results_20231201_140000.csv
```

## Data Fields

Each apartment listing includes the following information:

| Field | Description | Example |
|-------|-------------|---------|
| `address` | Full address | "Södermalm, Stockholm" |
| `price` | Asking price in SEK | 3500000 |
| `fee` | Monthly fee in SEK | 4200 |
| `price_per_m2` | Price per square meter | 58333 |
| `rooms` | Number of rooms | 2 |
| `living_area` | Living area in m² | 60 |
| `year_built` | Construction year | 1925 |
| `housing_cooperative` | Name of cooperative | "Brf Gamla Stan" |
| `floor` | Floor number | 3 |
| `total_floors` | Total floors in building | 6 |
| `has_elevator` | Elevator available | true/false |
| `has_balcony` | Balcony/patio available | true/false |
| `metro_distance` | Distance to metro (meters) | 250 |
| `bus_distance` | Distance to bus stop (meters) | 100 |
| `url` | Original listing URL | "https://..." |

## Analysis & Scoring

The analyzer uses a weighted scoring system based on four key areas:

### Scoring Components

1. **Price Score (40% default weight)**
   - Lower price = higher score
   - Considers both absolute price and price per m²

2. **Location Score (30% default weight)**
   - Proximity to public transport
   - Metro access weighted higher than bus access

3. **Size Score (20% default weight)**
   - Living area and number of rooms
   - Larger apartments score higher

4. **Amenity Score (10% default weight)**
   - Elevator availability
   - Balcony/patio availability
   - Building age and floor position

### Customizing Weights

Modify the weights in `pidgeon/analysis/analyzer.py`:

```python
custom_weights = {
    'price_weight': 0.5,      # 50% weight on price
    'location_weight': 0.3,   # 30% weight on location
    'size_weight': 0.15,      # 15% weight on size
    'amenity_weight': 0.05    # 5% weight on amenities
}

analyzer = ApartmentAnalyzer(weights=custom_weights)
```

## Development

### Project Structure

```
pidgeon/
├── pidgeon/                    # Main Python package
│   ├── spiders/               # Scrapy spiders
│   │   ├── hemnet.py         # Hemnet scraper
│   │   └── booli.py          # Booli scraper
│   ├── analysis/             # Analysis module
│   │   ├── analyzer.py       # Scoring algorithms
│   │   └── cli.py            # Command-line interface
│   ├── items.py              # Data models
│   ├── pipelines.py          # Data processing pipelines
│   └── settings.py           # Scrapy configuration
├── tests/                     # Unit tests
├── output/                    # Generated CSV files
├── requirements.txt           # Python dependencies
├── Makefile                   # Task automation
└── scrapy.cfg                # Scrapy project config
```

### Adding New Websites

1. Create a new spider in `pidgeon/spiders/`
2. Follow the existing spider pattern
3. Ensure data maps to the `ApartmentItem` fields
4. Add appropriate selectors for the website structure

### Running Tests

```bash
# Run all tests
make test

# Run specific test suites
make test-unit
make test-analysis

# Run with coverage
make test-coverage
```

### Code Quality

```bash
# Lint code
make lint

# Format code
make format
```

### Debugging

```bash
# Start interactive Scrapy shell
make shell

# Debug specific websites
make shell-hemnet  # Opens Hemnet in Scrapy shell
make shell-booli   # Opens Booli in Scrapy shell
```

## Configuration

### Scrapy Settings

Key settings in `pidgeon/settings.py`:

```python
# Rate limiting (important!)
DOWNLOAD_DELAY = 2                    # 2 second delay between requests
RANDOMIZE_DOWNLOAD_DELAY = 0.5       # Randomize delay (0.5 * to 1.5 * DOWNLOAD_DELAY)

# Concurrent requests
CONCURRENT_REQUESTS = 1              # One request at a time
CONCURRENT_REQUESTS_PER_DOMAIN = 1   # One per domain

# User agent rotation
USER_AGENT_LIST = [...]              # Multiple user agents to rotate
```

### Rate Limiting

⚠️ **Important**: Always respect website rate limits to avoid being blocked:

- Default delay: 2 seconds between requests
- Randomized delays to appear more human-like
- Single concurrent request per domain
- User agent rotation

## Troubleshooting

### Common Issues

#### Spider Not Finding Data
- Website structure may have changed
- Check selectors in spider files
- Use `make shell-hemnet` or `make shell-booli` to debug

#### Permission Denied Errors
- Ensure output directory exists: `mkdir -p output`
- Check file permissions
- Make sure virtual environment is activated

#### Missing Dependencies
```bash
# Reinstall dependencies
make clean-venv
make setup
```

#### Rate Limiting Issues
- Increase `DOWNLOAD_DELAY` in settings.py
- Check if your IP is temporarily blocked
- Try again later

### Getting Help

1. Check the logs in the terminal output
2. Use Scrapy shell for debugging: `make shell`
3. Run tests to verify functionality: `make test`
4. Check the [Scrapy documentation](https://docs.scrapy.org/)

## Legal & Ethics

- This tool is for personal research purposes
- Respects robots.txt and rate limiting
- Users are responsible for complying with website terms of service
- Always scrape responsibly and ethically

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite: `make test`
6. Submit a pull request

## License

See LICENSE file for details.

---

**Happy apartment hunting! 🏠✨**
