# Beaming Bog 💩

A free, open-source SEO crawler and website analyser inspired by Screaming Frog. Built with Python using a modular architecture for performance and extensibility.

## Features

- 🕷️ **Multi-threaded crawling** - Fast parallel crawling with configurable workers
- 📊 **SEO Analysis** - Identifies missing meta tags, duplicate content, broken links, redirect chains, and more
- 🤖 **Robots.txt compliance** - Respects crawl delays and exclusions
- 📁 **Multiple export formats** - CSV, JSON, and HTML reports
- 🔄 **Smart retry logic** - Handles rate limiting (429 errors) gracefully
- 📈 **Detailed metrics** - Response times, page sizes, status codes, redirect chains

## Installation

1. Clone this repo:
```bash
git clone https://github.com/olleepalmer/beaming-bog
cd beaming-bog
```

2. Install requirements:
```bash
pip install -r requirements.txt
```

## Usage

### Interactive Mode
Simply run without arguments to be prompted for a URL:
```bash
python beaming_bog.py
```

### Command Line Mode
```bash
python beaming_bog.py https://example.com [options]
```

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `url` | URL to crawl (optional if using interactive mode) | - |
| `-w, --workers` | Number of concurrent workers | 10 |
| `-d, --depth` | Maximum crawl depth | 10 |
| `-m, --max-urls` | Maximum number of URLs to crawl | unlimited |
| `--no-robots` | Ignore robots.txt | respect robots.txt |
| `--no-redirects` | Don't follow redirects | follow redirects |
| `-f, --format` | Export format (csv, json, html) | csv |
| `-o, --output` | Output file path | domain_timestamp.format |
| `-c, --config` | Configuration file path (JSON) | - |
| `-v, --verbose` | Enable verbose logging | - |

### Examples

Crawl with 20 workers and export as HTML:
```bash
python beaming_bog.py https://example.com -w 20 -f html
```

Limit crawl to 100 pages at depth 5:
```bash
python beaming_bog.py https://example.com -m 100 -d 5
```

Ignore robots.txt and save to specific file:
```bash
python beaming_bog.py https://example.com --no-robots -o my_crawl.csv
```

## SEO Analysis Features

The crawler automatically analyses each page for:

- **Missing/duplicate meta tags** - Title tags, meta descriptions
- **Content issues** - Duplicate content detection, thin content warnings
- **Technical SEO** - HTTP/HTTPS mixed content, redirect chains, 4xx/5xx errors
- **On-page elements** - H1/H2 structure, word counts, internal/external links
- **Performance** - Page load times, page sizes

## Output

The crawler generates comprehensive reports including:
- All scraped URLs with status codes
- Title tags and meta descriptions
- H1 and H2 headings
- Response times and page metrics
- Identified SEO issues
- Site-wide statistics and analysis

## Architecture

Beaming Bog v2.0 uses a modular architecture:
- `crawler.py` - Multi-threaded crawling engine
- `parser.py` - HTML parsing and link extraction
- `analyser.py` - SEO analysis and issue detection
- `exporter.py` - Multiple format export handlers
- `config.py` - Configuration management

## Questions, problems, concerns?

Let me know if you run into any issues! <op@publicbasic.com>