#!/usr/bin/env python3
"""
Beaming Bog v2 - A free Screaming Frog alternative
Main entry point using the new modular architecture
"""
import argparse
import logging
import sys
from pathlib import Path
from urllib.parse import urlparse
import time

from src.config import CrawlConfig
from src.crawler import Crawler
from src.parser import Parser
from src.analyser import Analyser
from src.exporter import Exporter


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sanitize_url(url: str) -> str:
    """Sanitize and validate URL"""
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    
    # Validate URL
    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")
    
    return url.lower().rstrip('/')


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='💩 Beaming Bog - SEO Crawler and Analyzer'
    )
    
    # Positional argument
    parser.add_argument(
        'url',
        nargs='?',
        help='URL to crawl (optional if using interactive mode)'
    )
    
    # Configuration options
    parser.add_argument(
        '-w', '--workers',
        type=int,
        default=10,
        help='Number of concurrent workers (default: 10)'
    )
    
    parser.add_argument(
        '-d', '--depth',
        type=int,
        default=10,
        help='Maximum crawl depth (default: 10)'
    )
    
    parser.add_argument(
        '-m', '--max-urls',
        type=int,
        help='Maximum number of URLs to crawl'
    )
    
    parser.add_argument(
        '--no-robots',
        action='store_true',
        help='Ignore robots.txt'
    )
    
    parser.add_argument(
        '--no-redirects',
        action='store_true',
        help="Don't follow redirects"
    )
    
    parser.add_argument(
        '-f', '--format',
        choices=['csv', 'json', 'html'],
        default='csv',
        help='Export format (default: csv)'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file path (default: domain_timestamp.format)'
    )
    
    parser.add_argument(
        '-c', '--config',
        help='Configuration file path (JSON)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Get URL
    if args.url:
        start_url = args.url
    else:
        # Interactive mode
        start_url = input("💩 Enter the URL: ")
    
    try:
        start_url = sanitize_url(start_url)
    except ValueError as e:
        logger.error(f"Invalid URL: {e}")
        sys.exit(1)
    
    # Load or create configuration
    if args.config:
        try:
            config = CrawlConfig.from_file(args.config)
            logger.info(f"Loaded configuration from {args.config}")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            sys.exit(1)
    else:
        config = CrawlConfig(
            max_workers=args.workers,
            max_depth=args.depth,
            max_urls=args.max_urls,
            respect_robots_txt=not args.no_robots,
            follow_redirects=not args.no_redirects,
            export_format=args.format
        )
    
    # Validate configuration
    issues = config.validate()
    if issues:
        logger.error("Configuration validation failed:")
        for issue in issues:
            logger.error(f"  - {issue}")
        sys.exit(1)
    
    # Initialize components
    crawler = Crawler(config)
    parser_instance = Parser(config)
    analyser = Analyser()
    exporter = Exporter(config.export_format)
    
    # Track crawl progress
    pages_crawled = 0
    pages_data = []
    metrics_data = []
    analyses = []
    
    def on_page_crawled(metrics, html_content):
        """Callback for each crawled page"""
        nonlocal pages_crawled
        pages_crawled += 1
        
        # Parse HTML
        parsed_data, links = parser_instance.parse(html_content, metrics.url)
        
        # Analyze page
        analysis = analyser.analyze_page(parsed_data, metrics)
        
        # Store data
        pages_data.append(parsed_data)
        metrics_data.append(metrics)
        analyses.append(analysis)
        
        # Print progress
        status_icon = "✅" if metrics.status_code == 200 else "❌"
        print(f"{status_icon} [{pages_crawled}] {metrics.url} - {metrics.status_code} - {len(analysis.issues)} issues")
        
        return parsed_data, links
    
    # Start crawling
    print(f"\n🕷️  Starting crawl of {start_url}")
    print(f"Configuration: {config.max_workers} workers, max depth {config.max_depth}")
    if config.respect_robots_txt:
        print("Respecting robots.txt")
    print("-" * 50)
    
    start_time = time.time()
    
    try:
        # Crawl the website
        crawler.crawl(start_url, on_page_crawled)
        
        # Perform site-wide analysis
        print("\n📊 Performing site-wide analysis...")
        site_analysis = analyser.analyze_site()
        
        # Determine output file
        if args.output:
            output_path = args.output
        else:
            domain = urlparse(start_url).netloc.replace('.', '_')
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            output_path = f"{domain}_{timestamp}"
        
        # Export results
        print(f"\n💾 Exporting results to {output_path}.{config.export_format}...")
        exported_file = exporter.export_crawl_data(
            pages_data,
            metrics_data,
            analyses,
            site_analysis,
            output_path
        )
        
        # Print summary
        elapsed_time = time.time() - start_time
        print("\n" + "=" * 50)
        print("✨ CRAWL COMPLETE!")
        print("=" * 50)
        print(f"📈 Statistics:")
        print(f"  • Pages crawled: {len(pages_data)}")
        print(f"  • Time elapsed: {elapsed_time:.2f} seconds")
        print(f"  • Pages per second: {len(pages_data) / elapsed_time:.2f}")
        
        if site_analysis.get('statistics'):
            stats = site_analysis['statistics']
            print(f"  • Average response time: {stats.get('avg_response_time_ms', 0):.0f}ms")
            print(f"  • Average word count: {stats.get('avg_word_count', 0):.0f}")
            print(f"  • Error pages: {stats.get('error_pages', 0)}")
            print(f"  • Redirect pages: {stats.get('redirect_pages', 0)}")
        
        # Issue summary
        total_issues = sum(len(a.issues) for a in analyses)
        error_count = sum(1 for a in analyses for i in a.issues if i.severity == 'error')
        warning_count = sum(1 for a in analyses for i in a.issues if i.severity == 'warning')
        
        print(f"\n⚠️  Issues found:")
        print(f"  • Total issues: {total_issues}")
        print(f"  • Errors: {error_count}")
        print(f"  • Warnings: {warning_count}")
        
        # Duplicate content
        if site_analysis.get('duplicates'):
            print(f"\n🔍 Duplicate content found:")
            for content_hash, urls in list(site_analysis['duplicates'].items())[:3]:
                print(f"  • {len(urls)} pages with identical content")
        
        print(f"\n📁 Results saved to: {exported_file}")
        print("\n💩 Happy SEO-ing!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Crawl interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Crawl failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()