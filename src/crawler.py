"""
Web crawler module with robots.txt support and redirect handling
"""
import time
import requests
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
from typing import Optional, Dict, List, Tuple, Set
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
import threading
from dataclasses import dataclass
import logging

from .config import CrawlConfig, ResponseMetrics


logger = logging.getLogger(__name__)


class RobotsChecker:
    """Handle robots.txt parsing and compliance"""
    
    def __init__(self, config: CrawlConfig):
        self.config = config
        self.robots_cache: Dict[str, RobotFileParser] = {}
        self.cache_lock = threading.Lock()
    
    def can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt"""
        if not self.config.respect_robots_txt:
            return True
        
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        with self.cache_lock:
            if base_url not in self.robots_cache:
                self.robots_cache[base_url] = self._fetch_robots_txt(base_url)
        
        rp = self.robots_cache[base_url]
        if rp is None:
            return True  # If no robots.txt, allow crawling
        
        return rp.can_fetch(self.config.user_agent, url)
    
    def get_crawl_delay(self, url: str) -> float:
        """Get crawl delay from robots.txt"""
        if not self.config.respect_robots_txt:
            return self.config.crawl_delay
        
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        with self.cache_lock:
            if base_url in self.robots_cache:
                rp = self.robots_cache[base_url]
                if rp and rp.crawl_delay(self.config.user_agent):
                    return float(rp.crawl_delay(self.config.user_agent))
        
        return self.config.crawl_delay
    
    def _fetch_robots_txt(self, base_url: str) -> Optional[RobotFileParser]:
        """Fetch and parse robots.txt file"""
        robots_url = urljoin(base_url, '/robots.txt')
        rp = RobotFileParser()
        rp.set_url(robots_url)
        
        try:
            rp.read()
            return rp
        except Exception as e:
            logger.debug(f"Could not fetch robots.txt from {robots_url}: {e}")
            return None


class Crawler:
    """Main crawler class handling HTTP requests and queue management"""
    
    def __init__(self, config: CrawlConfig):
        self.config = config
        self.session = self._create_session()
        self.robots_checker = RobotsChecker(config)
        
        # Queues and tracking
        self.to_visit: Queue = Queue()
        self.visited: Set[str] = set()
        self.visited_lock = threading.Lock()
        
        # Results storage
        self.results: List[Tuple[ResponseMetrics, str]] = []
        self.results_lock = threading.Lock()

        # Retry queue for 429 errors
        self.retry_urls: List[Tuple[str, int]] = []
        self.retry_lock = threading.Lock()

        # Rate limiting
        self.last_request_time: Dict[str, float] = {}
        self.rate_limit_lock = threading.Lock()
    
    def _create_session(self) -> requests.Session:
        """Create configured requests session"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': self.config.user_agent
        })
        session.max_redirects = self.config.max_redirects if self.config.follow_redirects else 0
        return session
    
    def fetch(self, url: str, depth: int = 0) -> Tuple[Optional[ResponseMetrics], Optional[str]]:
        """Fetch a single URL and return metrics and content"""
        
        # Check robots.txt
        if not self.robots_checker.can_fetch(url):
            logger.info(f"Blocked by robots.txt: {url}")
            return None, None
        
        # Apply rate limiting
        self._apply_rate_limit(url)
        
        # Track redirect chain
        redirect_chain = []
        
        try:
            start_time = time.time()
            
            # Make request
            response = self.session.get(
                url,
                timeout=self.config.timeout,
                allow_redirects=self.config.follow_redirects
            )
            
            # Track redirects
            if response.history:
                redirect_chain = [r.url for r in response.history]
            
            # Calculate metrics
            response_time_ms = (time.time() - start_time) * 1000
            
            metrics = ResponseMetrics(
                url=url,
                final_url=response.url,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                page_size_bytes=len(response.content),
                redirect_count=len(redirect_chain),
                redirect_chain=redirect_chain,
                content_type=response.headers.get('Content-Type', ''),
                encoding=response.encoding or 'utf-8',
                headers=dict(response.headers)
            )
            
            # Handle 429 Too Many Requests
            if response.status_code == 429:
                logger.info(f"Got 429 for {url}, will retry later")
                with self.retry_lock:
                    self.retry_urls.append((url, depth))
                return None, None

            # Only return content for HTML pages
            if 'text/html' in metrics.content_type:
                return metrics, response.text
            else:
                return metrics, None

        except requests.exceptions.TooManyRedirects:
            logger.warning(f"Too many redirects for {url}")
            metrics = ResponseMetrics(
                url=url,
                final_url=url,
                status_code=0,
                response_time_ms=0,
                page_size_bytes=0,
                redirect_count=self.config.max_redirects,
                redirect_chain=redirect_chain
            )
            return metrics, None
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching {url}")
            metrics = ResponseMetrics(
                url=url,
                final_url=url,
                status_code=0,
                response_time_ms=self.config.timeout * 1000,
                page_size_bytes=0,
                redirect_count=0
            )
            return metrics, None
            
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None, None
    
    def _apply_rate_limit(self, url: str):
        """Apply rate limiting based on crawl delay"""
        parsed = urlparse(url)
        domain = parsed.netloc
        
        delay = self.robots_checker.get_crawl_delay(url)
        if delay <= 0:
            return
        
        with self.rate_limit_lock:
            if domain in self.last_request_time:
                elapsed = time.time() - self.last_request_time[domain]
                if elapsed < delay:
                    time.sleep(delay - elapsed)
            self.last_request_time[domain] = time.time()
    
    def crawl(self, start_url: str, on_page_crawled=None) -> List[Tuple[ResponseMetrics, Dict]]:
        """
        Crawl website starting from start_url
        on_page_crawled: Optional callback function(metrics, parsed_data, links)
        """
        # Normalize and add start URL
        start_url = self._normalize_url(start_url)
        self.to_visit.put((start_url, 0))  # (url, depth)

        # First pass with multiple threads
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            workers = [executor.submit(self._worker, on_page_crawled) for _ in range(self.config.max_workers)]
            self.to_visit.join()

        # Handle retry URLs if any (with fewer workers to be polite)
        if self.retry_urls:
            logger.info(f"Retrying {len(self.retry_urls)} URLs that returned 429")
            retry_workers = min(5, self.config.max_workers)  # Use fewer workers for retries

            # Add retry URLs back to queue
            with self.retry_lock:
                for url, depth in self.retry_urls:
                    self.to_visit.put((url, depth))
                self.retry_urls.clear()

            # Process retries with reduced workers
            with ThreadPoolExecutor(max_workers=retry_workers) as executor:
                workers = [executor.submit(self._worker, on_page_crawled) for _ in range(retry_workers)]
                self.to_visit.join()

        return self.results
    
    def _worker(self, on_page_crawled):
        """Worker thread for crawling"""
        while True:
            try:
                url, depth = self.to_visit.get(timeout=2)  # 2 second timeout

                # Check if already visited
                with self.visited_lock:
                    if url in self.visited:
                        self.to_visit.task_done()
                        continue

                    # Check max URLs limit
                    if self.config.max_urls and len(self.visited) >= self.config.max_urls:
                        self.to_visit.task_done()
                        break

                    self.visited.add(url)

                # Check max depth
                if depth > self.config.max_depth:
                    self.to_visit.task_done()
                    continue

                # Fetch the page
                metrics, html_content = self.fetch(url)

                if metrics:
                    # Store results
                    with self.results_lock:
                        self.results.append((metrics, html_content))

                    # Callback for processing
                    if on_page_crawled and html_content:
                        parsed_data, links = on_page_crawled(metrics, html_content)

                        # Add discovered links to queue
                        for link in links:
                            normalized = self._normalize_url(link)
                            if self._should_crawl(normalized):
                                self.to_visit.put((normalized, depth + 1))

                self.to_visit.task_done()

            except Exception:  # Queue.Empty or other exceptions
                break
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for consistency"""
        # Remove fragment
        if '#' in url:
            url = url.split('#')[0]
        
        # Remove trailing slash
        url = url.rstrip('/')
        
        # Lowercase
        return url.lower()
    
    def _should_crawl(self, url: str) -> bool:
        """Check if URL should be crawled based on config"""
        # Check extensions
        for ext in self.config.excluded_extensions:
            if url.lower().endswith(f'.{ext}'):
                return False
        
        # Check patterns
        for pattern in self.config.excluded_patterns:
            if pattern in url.lower():
                return False
        
        return True