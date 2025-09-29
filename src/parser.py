"""
HTML parser module for extracting SEO-relevant data
"""
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional, Any, Tuple
import re
import logging

from .config import CrawlConfig, ResponseMetrics


logger = logging.getLogger(__name__)


class Parser:
    """Parse HTML and extract SEO-relevant data"""
    
    def __init__(self, config: CrawlConfig):
        self.config = config
    
    def parse(self, html: str, base_url: str) -> Tuple[Dict[str, Any], List[str]]:
        """
        Parse HTML and extract data based on configuration
        Returns: (parsed_data, discovered_links)
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        data = {
            'url': base_url
        }
        
        # Extract title
        data['title'] = self._extract_title(soup)
        data['title_length'] = len(data['title']) if data['title'] else 0
        
        # Extract meta tags
        if self.config.extract_meta_tags:
            data.update(self._extract_meta_tags(soup))
        
        # Extract canonical URL
        if self.config.extract_canonical:
            data['canonical'] = self._extract_canonical(soup)
        
        # Extract robots meta
        if self.config.extract_robots_meta:
            robots_data = self._extract_robots_meta(soup)
            data.update(robots_data)
        
        # Extract headers
        headers_data = self._extract_headers(soup)
        data.update(headers_data)
        
        # Extract Open Graph tags
        if self.config.extract_open_graph:
            og_data = self._extract_open_graph(soup)
            data.update(og_data)
        
        # Extract Twitter Cards
        if self.config.extract_twitter_cards:
            twitter_data = self._extract_twitter_cards(soup)
            data.update(twitter_data)
        
        # Extract links
        links, link_data = self._extract_links(soup, base_url)
        data.update(link_data)
        
        # Extract content metrics
        content_metrics = self._extract_content_metrics(soup)
        data.update(content_metrics)
        
        return data, links
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page title"""
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()
        return None
    
    def _extract_meta_tags(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract standard meta tags"""
        meta_data = {}
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            content = meta_desc.get('content', '').strip()
            meta_data['meta_description'] = content
            meta_data['meta_description_length'] = len(content)
        else:
            meta_data['meta_description'] = None
            meta_data['meta_description_length'] = 0
        
        # Meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            meta_data['meta_keywords'] = meta_keywords.get('content', '').strip()
        
        # Viewport
        meta_viewport = soup.find('meta', attrs={'name': 'viewport'})
        meta_data['has_viewport'] = meta_viewport is not None
        if meta_viewport:
            meta_data['viewport'] = meta_viewport.get('content', '').strip()
        
        # Charset
        charset = soup.find('meta', attrs={'charset': True})
        if charset:
            meta_data['charset'] = charset.get('charset')
        else:
            charset = soup.find('meta', attrs={'http-equiv': 'Content-Type'})
            if charset:
                content = charset.get('content', '')
                match = re.search(r'charset=([^;]+)', content)
                if match:
                    meta_data['charset'] = match.group(1).strip()
        
        return meta_data
    
    def _extract_canonical(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract canonical URL"""
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        if canonical:
            return canonical.get('href')
        return None
    
    def _extract_robots_meta(self, soup: BeautifulSoup) -> Dict[str, bool]:
        """Extract robots meta directives"""
        robots_data = {
            'meta_robots_noindex': False,
            'meta_robots_nofollow': False,
            'meta_robots_noarchive': False,
            'meta_robots_nosnippet': False,
            'meta_robots_noimageindex': False
        }
        
        robots_meta = soup.find('meta', attrs={'name': 'robots'})
        if robots_meta:
            content = robots_meta.get('content', '').lower()
            robots_data['meta_robots'] = content
            
            if 'noindex' in content:
                robots_data['meta_robots_noindex'] = True
            if 'nofollow' in content:
                robots_data['meta_robots_nofollow'] = True
            if 'noarchive' in content:
                robots_data['meta_robots_noarchive'] = True
            if 'nosnippet' in content:
                robots_data['meta_robots_nosnippet'] = True
            if 'noimageindex' in content:
                robots_data['meta_robots_noimageindex'] = True
        
        return robots_data
    
    def _extract_headers(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract header tags (H1-H6)"""
        headers_data = {}
        
        for header_tag in self.config.extract_headers:
            headers = soup.find_all(header_tag)
            
            # Store count
            headers_data[f'{header_tag}_count'] = len(headers)
            
            # Store individual headers
            for i, header in enumerate(headers, 1):
                text = header.get_text().strip()
                headers_data[f'{header_tag}_{i}'] = text
                headers_data[f'{header_tag}_{i}_length'] = len(text)
        
        # Special handling for H1 (most important for SEO)
        h1_tags = soup.find_all('h1')
        if h1_tags:
            headers_data['h1_first'] = h1_tags[0].get_text().strip()
            headers_data['h1_first_length'] = len(headers_data['h1_first'])
        
        return headers_data
    
    def _extract_open_graph(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract Open Graph meta tags"""
        og_data = {}
        
        og_tags = soup.find_all('meta', attrs={'property': re.compile(r'^og:')})
        
        for tag in og_tags:
            prop = tag.get('property', '').replace('og:', 'og_')
            content = tag.get('content', '').strip()
            og_data[prop] = content
        
        # Check if Open Graph is present
        og_data['has_open_graph'] = len(og_tags) > 0
        
        return og_data
    
    def _extract_twitter_cards(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract Twitter Card meta tags"""
        twitter_data = {}
        
        twitter_tags = soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')})
        
        for tag in twitter_tags:
            name = tag.get('name', '').replace('twitter:', 'twitter_')
            content = tag.get('content', '').strip()
            twitter_data[name] = content
        
        # Check if Twitter Cards are present
        twitter_data['has_twitter_cards'] = len(twitter_tags) > 0
        
        return twitter_data
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> Tuple[List[str], Dict[str, Any]]:
        """Extract and analyze links"""
        internal_links = []
        external_links = []
        all_links = []
        
        base_domain = urlparse(base_url).netloc
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').strip()
            if not href:
                continue
            
            # Resolve relative URLs
            absolute_url = urljoin(base_url, href)
            
            # Skip certain types of links
            if href.startswith('mailto:') or href.startswith('tel:') or href.startswith('javascript:'):
                continue
            
            # Check if internal or external
            link_domain = urlparse(absolute_url).netloc
            
            if link_domain == base_domain:
                internal_links.append(absolute_url)
                all_links.append(absolute_url)
            else:
                external_links.append(absolute_url)
        
        link_data = {
            'internal_links_count': len(internal_links),
            'external_links_count': len(external_links),
            'total_links_count': len(internal_links) + len(external_links)
        }
        
        # Return internal links for crawling
        return all_links, link_data
    
    def _extract_content_metrics(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract content-related metrics"""
        metrics = {}
        
        # Get all text content
        text_content = soup.get_text()
        
        # Clean up text
        text_content = ' '.join(text_content.split())
        
        # Word count
        words = text_content.split()
        metrics['word_count'] = len(words)
        
        # Image count
        images = soup.find_all('img')
        metrics['image_count'] = len(images)
        
        # Images without alt text
        images_no_alt = [img for img in images if not img.get('alt')]
        metrics['images_without_alt'] = len(images_no_alt)
        
        # Forms count
        forms = soup.find_all('form')
        metrics['form_count'] = len(forms)
        
        # Tables count
        tables = soup.find_all('table')
        metrics['table_count'] = len(tables)
        
        # iframes count
        iframes = soup.find_all('iframe')
        metrics['iframe_count'] = len(iframes)
        
        return metrics