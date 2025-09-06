# Pidgeon Apartment Scraper and Analyzer
# Makefile for managing common tasks

# Variables
PYTHON = python3
PIP = pip3
VENV = venv
VENV_BIN = $(VENV)/bin
SCRAPY = $(VENV_BIN)/scrapy
PYTHON_VENV = $(VENV_BIN)/python

# Default target
.PHONY: help
help:
	@echo "Pidgeon Apartment Scraper and Analyzer"
	@echo "======================================"
	@echo ""
	@echo "Available targets:"
	@echo "  setup         - Set up virtual environment and install dependencies"
	@echo "  install       - Install dependencies in existing virtual environment"
	@echo "  clean         - Clean up generated files and directories"
	@echo "  clean-venv    - Remove virtual environment"
	@echo ""
	@echo "Scraping targets:"
	@echo "  scrape-hemnet - Run Hemnet spider"
	@echo "  scrape-booli  - Run Booli spider"
	@echo "  scrape-all    - Run all spiders"
	@echo ""
	@echo "Analysis targets:"
	@echo "  analyze       - Analyze scraped data (specify INPUT_FILE=path/to/file.csv)"
	@echo "  analyze-latest - Analyze the most recent scraped data file"
	@echo ""
	@echo "Testing targets:"
	@echo "  test          - Run all tests"
	@echo "  test-unit     - Run unit tests only"
	@echo "  test-analysis - Run analysis module tests"
	@echo ""
	@echo "Development targets:"
	@echo "  lint          - Run code linting with flake8"
	@echo "  format        - Format code with black"
	@echo "  shell         - Start Scrapy shell for debugging"
	@echo ""
	@echo "Examples:"
	@echo "  make setup"
	@echo "  make scrape-hemnet"
	@echo "  make analyze INPUT_FILE=output/apartments_hemnet_20231201_120000.csv"
	@echo "  make analyze-latest"

# Setup and installation
.PHONY: setup
setup: $(VENV_BIN)/activate

$(VENV_BIN)/activate: requirements.txt
	@echo "Creating virtual environment..."
	$(PYTHON) -m venv $(VENV)
	@echo "Installing dependencies..."
	$(VENV_BIN)/pip install --upgrade pip
	$(VENV_BIN)/pip install -r requirements.txt
	@echo "Setup complete! Virtual environment created in $(VENV)/"

.PHONY: install
install:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi
	$(VENV_BIN)/pip install -r requirements.txt

# Create output directory
output:
	mkdir -p output

# Scraping targets
.PHONY: scrape-hemnet
scrape-hemnet: $(VENV_BIN)/activate output
	@echo "Starting Hemnet spider..."
	cd $(CURDIR) && $(SCRAPY) crawl hemnet

.PHONY: scrape-booli
scrape-booli: $(VENV_BIN)/activate output
	@echo "Starting Booli spider..."
	cd $(CURDIR) && $(SCRAPY) crawl booli

.PHONY: scrape-all
scrape-all: scrape-hemnet scrape-booli

.PHONY: scrape-hemnet-url
scrape-hemnet-url: $(VENV_BIN)/activate output
	@if [ -z "$(URL)" ]; then \
		echo "Usage: make scrape-hemnet-url URL='https://www.hemnet.se/...'"; \
		exit 1; \
	fi
	@echo "Starting Hemnet spider with custom URL..."
	cd $(CURDIR) && $(SCRAPY) crawl hemnet -a search_url="$(URL)"

.PHONY: scrape-booli-url
scrape-booli-url: $(VENV_BIN)/activate output
	@if [ -z "$(URL)" ]; then \
		echo "Usage: make scrape-booli-url URL='https://www.booli.se/...'"; \
		exit 1; \
	fi
	@echo "Starting Booli spider with custom URL..."
	cd $(CURDIR) && $(SCRAPY) crawl booli -a search_url="$(URL)"

# Analysis targets
.PHONY: analyze
analyze: $(VENV_BIN)/activate
	@if [ -z "$(INPUT_FILE)" ]; then \
		echo "Usage: make analyze INPUT_FILE=path/to/file.csv"; \
		echo "Or use: make analyze-latest"; \
		exit 1; \
	fi
	@if [ ! -f "$(INPUT_FILE)" ]; then \
		echo "File not found: $(INPUT_FILE)"; \
		exit 1; \
	fi
	@echo "Analyzing apartment data from $(INPUT_FILE)..."
	$(PYTHON_VENV) -m pidgeon.analysis.cli analyze "$(INPUT_FILE)"

.PHONY: analyze-latest
analyze-latest: $(VENV_BIN)/activate
	@echo "Finding latest scraped data file..."
	@LATEST_FILE=$$(ls -t output/apartments_*.csv 2>/dev/null | head -n 1); \
	if [ -z "$$LATEST_FILE" ]; then \
		echo "No scraped data files found in output/"; \
		echo "Run 'make scrape-hemnet' or 'make scrape-booli' first."; \
		exit 1; \
	fi; \
	echo "Analyzing latest file: $$LATEST_FILE"; \
	$(PYTHON_VENV) -m pidgeon.analysis.cli analyze "$$LATEST_FILE"

.PHONY: analyze-custom
analyze-custom: $(VENV_BIN)/activate
	@if [ -z "$(INPUT_FILE)" ]; then \
		echo "Usage: make analyze-custom INPUT_FILE=file.csv [MAX_PRICE=4000000] [MAX_FEE=5000] [MIN_ROOMS=2] [MAX_ROOMS=4]"; \
		exit 1; \
	fi
	@ARGS="$(INPUT_FILE)"; \
	if [ ! -z "$(MAX_PRICE)" ]; then ARGS="$$ARGS --max-price $(MAX_PRICE)"; fi; \
	if [ ! -z "$(MAX_FEE)" ]; then ARGS="$$ARGS --max-fee $(MAX_FEE)"; fi; \
	if [ ! -z "$(MIN_ROOMS)" ]; then ARGS="$$ARGS --min-rooms $(MIN_ROOMS)"; fi; \
	if [ ! -z "$(MAX_ROOMS)" ]; then ARGS="$$ARGS --max-rooms $(MAX_ROOMS)"; fi; \
	echo "Running custom analysis with parameters..."; \
	$(PYTHON_VENV) -m pidgeon.analysis.cli analyze $$ARGS

# Testing targets
.PHONY: test
test: $(VENV_BIN)/activate
	@if [ ! -f "$(VENV_BIN)/pytest" ]; then \
		echo "Installing pytest..."; \
		$(VENV_BIN)/pip install pytest pytest-cov; \
	fi
	$(VENV_BIN)/pytest tests/ -v

.PHONY: test-unit
test-unit: $(VENV_BIN)/activate
	@if [ ! -f "$(VENV_BIN)/pytest" ]; then \
		echo "Installing pytest..."; \
		$(VENV_BIN)/pip install pytest pytest-cov; \
	fi
	$(VENV_BIN)/pytest tests/unit/ -v

.PHONY: test-analysis
test-analysis: $(VENV_BIN)/activate
	@if [ ! -f "$(VENV_BIN)/pytest" ]; then \
		echo "Installing pytest..."; \
		$(VENV_BIN)/pip install pytest pytest-cov; \
	fi
	$(VENV_BIN)/pytest tests/test_analysis.py -v

.PHONY: test-coverage
test-coverage: $(VENV_BIN)/activate
	@if [ ! -f "$(VENV_BIN)/pytest" ]; then \
		echo "Installing pytest..."; \
		$(VENV_BIN)/pip install pytest pytest-cov; \
	fi
	$(VENV_BIN)/pytest tests/ --cov=pidgeon --cov-report=html --cov-report=term

# Development targets
.PHONY: lint
lint: $(VENV_BIN)/activate
	@if [ ! -f "$(VENV_BIN)/flake8" ]; then \
		echo "Installing flake8..."; \
		$(VENV_BIN)/pip install flake8; \
	fi
	$(VENV_BIN)/flake8 pidgeon/ tests/ --max-line-length=88 --ignore=E203,W503

.PHONY: format
format: $(VENV_BIN)/activate
	@if [ ! -f "$(VENV_BIN)/black" ]; then \
		echo "Installing black..."; \
		$(VENV_BIN)/pip install black; \
	fi
	$(VENV_BIN)/black pidgeon/ tests/

.PHONY: shell
shell: $(VENV_BIN)/activate
	@echo "Starting Scrapy shell..."
	cd $(CURDIR) && $(SCRAPY) shell

.PHONY: shell-hemnet
shell-hemnet: $(VENV_BIN)/activate
	@echo "Starting Scrapy shell with Hemnet URL..."
	cd $(CURDIR) && $(SCRAPY) shell "https://www.hemnet.se/bostader?location_ids%5B%5D=17744"

.PHONY: shell-booli
shell-booli: $(VENV_BIN)/activate
	@echo "Starting Scrapy shell with Booli URL..."
	cd $(CURDIR) && $(SCRAPY) shell "https://www.booli.se/slutpriser/stockholm/"

# Cleanup targets
.PHONY: clean
clean:
	@echo "Cleaning up generated files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage

.PHONY: clean-output
clean-output:
	@echo "Cleaning output files..."
	rm -rf output/*.csv

.PHONY: clean-venv
clean-venv:
	@echo "Removing virtual environment..."
	rm -rf $(VENV)

.PHONY: clean-all
clean-all: clean clean-output clean-venv

# Status and info targets
.PHONY: status
status:
	@echo "Pidgeon Project Status"
	@echo "====================="
	@echo "Virtual environment: $(if $(wildcard $(VENV_BIN)/activate),✓ Present,✗ Missing)"
	@echo "Dependencies: $(if $(wildcard $(VENV_BIN)/scrapy),✓ Installed,✗ Not installed)"
	@echo "Output directory: $(if $(wildcard output/),✓ Present,✗ Missing)"
	@echo ""
	@if [ -d "output/" ]; then \
		echo "Output files:"; \
		ls -la output/*.csv 2>/dev/null || echo "  No CSV files found"; \
	fi

.PHONY: list-output
list-output:
	@echo "Available output files:"
	@ls -la output/*.csv 2>/dev/null || echo "No CSV files found in output/"

# Quick start target
.PHONY: quickstart
quickstart: setup
	@echo ""
	@echo "Quick start complete! 🚀"
	@echo ""
	@echo "Next steps:"
	@echo "1. Run a scraper:     make scrape-hemnet"
	@echo "2. Analyze results:   make analyze-latest"
	@echo "3. View help:         make help"
	@echo ""

