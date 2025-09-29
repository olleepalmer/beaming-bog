"""
SEO analysis module for identifying issues and opportunities
"""
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
import hashlib
import logging

from .config import ResponseMetrics


logger = logging.getLogger(__name__)


@dataclass
class SEOIssue:
    """Represents an SEO issue found during analysis"""
    severity: str  # 'error', 'warning', 'info'
    category: str  # 'title', 'meta', 'content', 'technical', etc.
    issue: str
    details: str
    url: str
    recommendation: str = ""


@dataclass 
class PageAnalysis:
    """Analysis results for a single page"""
    url: str
    issues: List[SEOIssue] = field(default_factory=list)
    score: int = 100  # SEO score out of 100
    metrics: Dict[str, Any] = field(default_factory=dict)


class Analyzer:
    """Analyze crawled data for SEO issues and opportunities"""
    
    # SEO best practice thresholds
    TITLE_MIN_LENGTH = 30
    TITLE_MAX_LENGTH = 60
    TITLE_WARNING_MAX = 70
    
    META_DESC_MIN_LENGTH = 120
    META_DESC_MAX_LENGTH = 160
    META_DESC_WARNING_MAX = 170
    
    H1_MIN_LENGTH = 20
    H1_MAX_LENGTH = 70
    
    MIN_WORD_COUNT = 300
    GOOD_WORD_COUNT = 600
    
    MAX_RESPONSE_TIME_MS = 3000
    WARNING_RESPONSE_TIME_MS = 1500
    
    def __init__(self):
        self.all_pages: List[Dict[str, Any]] = []
        self.all_metrics: List[ResponseMetrics] = []
        self.content_hashes: Dict[str, List[str]] = {}  # For duplicate detection
    
    def analyze_page(self, parsed_data: Dict[str, Any], metrics: ResponseMetrics) -> PageAnalysis:
        """Analyze a single page for SEO issues"""
        analysis = PageAnalysis(url=metrics.url)
        
        # Technical checks
        self._check_response_metrics(analysis, metrics)
        self._check_redirects(analysis, metrics)
        
        # On-page SEO checks
        self._check_title(analysis, parsed_data)
        self._check_meta_description(analysis, parsed_data)
        self._check_headers(analysis, parsed_data)
        self._check_meta_robots(analysis, parsed_data)
        self._check_canonical(analysis, parsed_data)
        self._check_content(analysis, parsed_data)
        self._check_images(analysis, parsed_data)
        self._check_links(analysis, parsed_data)
        
        # Calculate SEO score
        analysis.score = self._calculate_seo_score(analysis)
        
        # Store for site-wide analysis
        self.all_pages.append(parsed_data)
        self.all_metrics.append(metrics)
        
        return analysis
    
    def analyze_site(self) -> Dict[str, Any]:
        """Perform site-wide analysis after all pages are crawled"""
        site_analysis = {
            'total_pages': len(self.all_pages),
            'issues': [],
            'duplicates': {},
            'orphan_pages': [],
            'redirect_chains': [],
            'broken_links': [],
            'statistics': {}
        }
        
        # Find duplicate content
        site_analysis['duplicates'] = self._find_duplicate_content()
        
        # Find duplicate titles
        duplicate_titles = self._find_duplicate_titles()
        if duplicate_titles:
            site_analysis['issues'].append({
                'type': 'duplicate_titles',
                'count': len(duplicate_titles),
                'urls': duplicate_titles
            })
        
        # Find duplicate meta descriptions
        duplicate_metas = self._find_duplicate_meta_descriptions()
        if duplicate_metas:
            site_analysis['issues'].append({
                'type': 'duplicate_meta_descriptions', 
                'count': len(duplicate_metas),
                'urls': duplicate_metas
            })
        
        # Find orphan pages (pages with no internal links pointing to them)
        site_analysis['orphan_pages'] = self._find_orphan_pages()
        
        # Find redirect chains
        site_analysis['redirect_chains'] = self._find_redirect_chains()
        
        # Find broken links
        site_analysis['broken_links'] = self._find_broken_links()
        
        # Calculate statistics
        site_analysis['statistics'] = self._calculate_site_statistics()
        
        return site_analysis
    
    def _check_response_metrics(self, analysis: PageAnalysis, metrics: ResponseMetrics):
        """Check response time and status codes"""
        
        # Status code checks
        if metrics.status_code >= 400:
            analysis.issues.append(SEOIssue(
                severity='error',
                category='technical',
                issue=f'HTTP {metrics.status_code} Error',
                details=f'Page returned status code {metrics.status_code}',
                url=metrics.url,
                recommendation='Fix the error or remove links to this page'
            ))
        elif metrics.status_code >= 300 and metrics.status_code < 400:
            if metrics.redirect_count == 0:
                analysis.issues.append(SEOIssue(
                    severity='warning',
                    category='technical',
                    issue='Redirect not followed',
                    details=f'Page has {metrics.status_code} redirect',
                    url=metrics.url,
                    recommendation='Update links to point to the final destination'
                ))
        
        # Response time checks
        if metrics.response_time_ms > self.MAX_RESPONSE_TIME_MS:
            analysis.issues.append(SEOIssue(
                severity='error',
                category='technical',
                issue='Slow response time',
                details=f'Response time: {metrics.response_time_ms:.0f}ms',
                url=metrics.url,
                recommendation='Optimize server response time to under 3 seconds'
            ))
        elif metrics.response_time_ms > self.WARNING_RESPONSE_TIME_MS:
            analysis.issues.append(SEOIssue(
                severity='warning',
                category='technical',
                issue='Response time could be improved',
                details=f'Response time: {metrics.response_time_ms:.0f}ms',
                url=metrics.url,
                recommendation='Consider optimizing to under 1.5 seconds'
            ))
    
    def _check_redirects(self, analysis: PageAnalysis, metrics: ResponseMetrics):
        """Check for redirect issues"""
        if metrics.redirect_count > 2:
            analysis.issues.append(SEOIssue(
                severity='error',
                category='technical',
                issue='Redirect chain too long',
                details=f'Page has {metrics.redirect_count} redirects',
                url=metrics.url,
                recommendation='Reduce redirect chain to maximum 2 hops'
            ))
        elif metrics.redirect_count > 0:
            analysis.issues.append(SEOIssue(
                severity='info',
                category='technical',
                issue='Page has redirects',
                details=f'Page redirects {metrics.redirect_count} time(s) to {metrics.final_url}',
                url=metrics.url,
                recommendation='Consider updating links to point directly to final URL'
            ))
    
    def _check_title(self, analysis: PageAnalysis, parsed_data: Dict[str, Any]):
        """Check title tag SEO"""
        title = parsed_data.get('title')
        title_length = parsed_data.get('title_length', 0)
        
        if not title:
            analysis.issues.append(SEOIssue(
                severity='error',
                category='title',
                issue='Missing title tag',
                details='Page has no title tag',
                url=analysis.url,
                recommendation='Add a unique, descriptive title tag'
            ))
        elif title_length < self.TITLE_MIN_LENGTH:
            analysis.issues.append(SEOIssue(
                severity='warning',
                category='title',
                issue='Title too short',
                details=f'Title is {title_length} characters (minimum recommended: {self.TITLE_MIN_LENGTH})',
                url=analysis.url,
                recommendation='Expand title to be more descriptive'
            ))
        elif title_length > self.TITLE_WARNING_MAX:
            analysis.issues.append(SEOIssue(
                severity='error',
                category='title',
                issue='Title too long',
                details=f'Title is {title_length} characters (maximum recommended: {self.TITLE_MAX_LENGTH})',
                url=analysis.url,
                recommendation='Shorten title to prevent truncation in search results'
            ))
        elif title_length > self.TITLE_MAX_LENGTH:
            analysis.issues.append(SEOIssue(
                severity='warning',
                category='title',
                issue='Title may be truncated',
                details=f'Title is {title_length} characters',
                url=analysis.url,
                recommendation=f'Consider shortening to {self.TITLE_MAX_LENGTH} characters'
            ))
    
    def _check_meta_description(self, analysis: PageAnalysis, parsed_data: Dict[str, Any]):
        """Check meta description SEO"""
        meta_desc = parsed_data.get('meta_description')
        meta_length = parsed_data.get('meta_description_length', 0)
        
        if not meta_desc:
            analysis.issues.append(SEOIssue(
                severity='warning',
                category='meta',
                issue='Missing meta description',
                details='Page has no meta description',
                url=analysis.url,
                recommendation='Add a compelling meta description'
            ))
        elif meta_length < self.META_DESC_MIN_LENGTH:
            analysis.issues.append(SEOIssue(
                severity='warning',
                category='meta',
                issue='Meta description too short',
                details=f'Meta description is {meta_length} characters (minimum recommended: {self.META_DESC_MIN_LENGTH})',
                url=analysis.url,
                recommendation='Expand meta description to be more descriptive'
            ))
        elif meta_length > self.META_DESC_WARNING_MAX:
            analysis.issues.append(SEOIssue(
                severity='error',
                category='meta',
                issue='Meta description too long',
                details=f'Meta description is {meta_length} characters (maximum recommended: {self.META_DESC_MAX_LENGTH})',
                url=analysis.url,
                recommendation='Shorten meta description to prevent truncation'
            ))
        elif meta_length > self.META_DESC_MAX_LENGTH:
            analysis.issues.append(SEOIssue(
                severity='warning',
                category='meta',
                issue='Meta description may be truncated',
                details=f'Meta description is {meta_length} characters',
                url=analysis.url,
                recommendation=f'Consider shortening to {self.META_DESC_MAX_LENGTH} characters'
            ))
    
    def _check_headers(self, analysis: PageAnalysis, parsed_data: Dict[str, Any]):
        """Check header tags SEO"""
        h1_count = parsed_data.get('h1_count', 0)
        h1_first = parsed_data.get('h1_first')
        h1_length = parsed_data.get('h1_first_length', 0)
        
        if h1_count == 0:
            analysis.issues.append(SEOIssue(
                severity='error',
                category='headers',
                issue='Missing H1 tag',
                details='Page has no H1 tag',
                url=analysis.url,
                recommendation='Add a descriptive H1 tag'
            ))
        elif h1_count > 1:
            analysis.issues.append(SEOIssue(
                severity='warning',
                category='headers',
                issue='Multiple H1 tags',
                details=f'Page has {h1_count} H1 tags',
                url=analysis.url,
                recommendation='Use only one H1 tag per page'
            ))
        
        if h1_first and h1_length < self.H1_MIN_LENGTH:
            analysis.issues.append(SEOIssue(
                severity='info',
                category='headers',
                issue='H1 tag too short',
                details=f'H1 is {h1_length} characters',
                url=analysis.url,
                recommendation='Consider making H1 more descriptive'
            ))
        elif h1_first and h1_length > self.H1_MAX_LENGTH:
            analysis.issues.append(SEOIssue(
                severity='info',
                category='headers',
                issue='H1 tag too long',
                details=f'H1 is {h1_length} characters',
                url=analysis.url,
                recommendation='Consider shortening H1 tag'
            ))
    
    def _check_meta_robots(self, analysis: PageAnalysis, parsed_data: Dict[str, Any]):
        """Check meta robots directives"""
        if parsed_data.get('meta_robots_noindex'):
            analysis.issues.append(SEOIssue(
                severity='warning',
                category='meta',
                issue='Page set to noindex',
                details='Meta robots tag contains noindex directive',
                url=analysis.url,
                recommendation='Remove noindex if page should be indexed'
            ))
        
        if parsed_data.get('meta_robots_nofollow'):
            analysis.issues.append(SEOIssue(
                severity='info',
                category='meta',
                issue='Page set to nofollow',
                details='Meta robots tag contains nofollow directive',
                url=analysis.url,
                recommendation='Consider if nofollow is necessary'
            ))
    
    def _check_canonical(self, analysis: PageAnalysis, parsed_data: Dict[str, Any]):
        """Check canonical URL"""
        canonical = parsed_data.get('canonical')
        
        if canonical and canonical != analysis.url:
            analysis.issues.append(SEOIssue(
                severity='info',
                category='meta',
                issue='Canonical URL differs from page URL',
                details=f'Canonical points to: {canonical}',
                url=analysis.url,
                recommendation='Verify canonical URL is correct'
            ))
    
    def _check_content(self, analysis: PageAnalysis, parsed_data: Dict[str, Any]):
        """Check content quality metrics"""
        word_count = parsed_data.get('word_count', 0)
        
        if word_count < self.MIN_WORD_COUNT:
            analysis.issues.append(SEOIssue(
                severity='warning',
                category='content',
                issue='Thin content',
                details=f'Page has only {word_count} words',
                url=analysis.url,
                recommendation=f'Add more content (minimum {self.MIN_WORD_COUNT} words recommended)'
            ))
        elif word_count < self.GOOD_WORD_COUNT:
            analysis.issues.append(SEOIssue(
                severity='info',
                category='content',
                issue='Content could be expanded',
                details=f'Page has {word_count} words',
                url=analysis.url,
                recommendation=f'Consider adding more content ({self.GOOD_WORD_COUNT}+ words for better SEO)'
            ))
    
    def _check_images(self, analysis: PageAnalysis, parsed_data: Dict[str, Any]):
        """Check image SEO"""
        images_without_alt = parsed_data.get('images_without_alt', 0)
        
        if images_without_alt > 0:
            analysis.issues.append(SEOIssue(
                severity='warning',
                category='images',
                issue='Images without alt text',
                details=f'{images_without_alt} image(s) missing alt text',
                url=analysis.url,
                recommendation='Add descriptive alt text to all images'
            ))
    
    def _check_links(self, analysis: PageAnalysis, parsed_data: Dict[str, Any]):
        """Check link-related SEO"""
        external_links = parsed_data.get('external_links_count', 0)
        internal_links = parsed_data.get('internal_links_count', 0)
        
        if internal_links == 0:
            analysis.issues.append(SEOIssue(
                severity='warning',
                category='links',
                issue='No internal links',
                details='Page has no internal links',
                url=analysis.url,
                recommendation='Add internal links to related content'
            ))
        
        if external_links > 100:
            analysis.issues.append(SEOIssue(
                severity='info',
                category='links',
                issue='Many external links',
                details=f'Page has {external_links} external links',
                url=analysis.url,
                recommendation='Review if all external links are necessary'
            ))
    
    def _calculate_seo_score(self, analysis: PageAnalysis) -> int:
        """Calculate SEO score based on issues found"""
        score = 100
        
        for issue in analysis.issues:
            if issue.severity == 'error':
                score -= 10
            elif issue.severity == 'warning':
                score -= 5
            elif issue.severity == 'info':
                score -= 2
        
        return max(0, score)
    
    def _find_duplicate_content(self) -> Dict[str, List[str]]:
        """Find pages with duplicate content using MD5 hashing"""
        content_hashes = {}
        
        for page in self.all_pages:
            # Create content hash from title + meta description + h1
            content_str = f"{page.get('title', '')}{page.get('meta_description', '')}{page.get('h1_first', '')}"
            content_hash = hashlib.md5(content_str.encode()).hexdigest()
            
            if content_hash not in content_hashes:
                content_hashes[content_hash] = []
            content_hashes[content_hash].append(page['url'])
        
        # Return only duplicates
        return {k: v for k, v in content_hashes.items() if len(v) > 1}
    
    def _find_duplicate_titles(self) -> Dict[str, List[str]]:
        """Find pages with duplicate titles"""
        titles = {}
        
        for page in self.all_pages:
            title = page.get('title')
            if title:
                if title not in titles:
                    titles[title] = []
                titles[title].append(page['url'])
        
        return {k: v for k, v in titles.items() if len(v) > 1}
    
    def _find_duplicate_meta_descriptions(self) -> Dict[str, List[str]]:
        """Find pages with duplicate meta descriptions"""
        metas = {}
        
        for page in self.all_pages:
            meta = page.get('meta_description')
            if meta:
                if meta not in metas:
                    metas[meta] = []
                metas[meta].append(page['url'])
        
        return {k: v for k, v in metas.items() if len(v) > 1}
    
    def _find_orphan_pages(self) -> List[str]:
        """Find pages with no internal links pointing to them"""
        all_urls = {page['url'] for page in self.all_pages}
        linked_urls = set()
        
        # Collect all internally linked URLs
        for page in self.all_pages:
            # This would need to be enhanced with actual link data
            pass
        
        return list(all_urls - linked_urls)
    
    def _find_redirect_chains(self) -> List[List[str]]:
        """Find redirect chains from metrics"""
        chains = []
        
        for metric in self.all_metrics:
            if len(metric.redirect_chain) > 1:
                chain = [metric.url] + metric.redirect_chain + [metric.final_url]
                chains.append(chain)
        
        return chains
    
    def _find_broken_links(self) -> List[Dict[str, Any]]:
        """Find broken links (4xx, 5xx status codes)"""
        broken = []
        
        for metric in self.all_metrics:
            if metric.status_code >= 400:
                broken.append({
                    'url': metric.url,
                    'status_code': metric.status_code
                })
        
        return broken
    
    def _calculate_site_statistics(self) -> Dict[str, Any]:
        """Calculate site-wide statistics"""
        stats = {
            'total_pages': len(self.all_pages),
            'avg_response_time_ms': 0,
            'avg_page_size_bytes': 0,
            'avg_word_count': 0,
            'pages_with_title': 0,
            'pages_with_meta_description': 0,
            'pages_with_h1': 0,
            'noindex_pages': 0,
            'redirect_pages': 0,
            'error_pages': 0
        }
        
        if self.all_metrics:
            stats['avg_response_time_ms'] = sum(m.response_time_ms for m in self.all_metrics) / len(self.all_metrics)
            stats['avg_page_size_bytes'] = sum(m.page_size_bytes for m in self.all_metrics) / len(self.all_metrics)
            stats['redirect_pages'] = sum(1 for m in self.all_metrics if m.redirect_count > 0)
            stats['error_pages'] = sum(1 for m in self.all_metrics if m.status_code >= 400)
        
        if self.all_pages:
            stats['avg_word_count'] = sum(p.get('word_count', 0) for p in self.all_pages) / len(self.all_pages)
            stats['pages_with_title'] = sum(1 for p in self.all_pages if p.get('title'))
            stats['pages_with_meta_description'] = sum(1 for p in self.all_pages if p.get('meta_description'))
            stats['pages_with_h1'] = sum(1 for p in self.all_pages if p.get('h1_count', 0) > 0)
            stats['noindex_pages'] = sum(1 for p in self.all_pages if p.get('meta_robots_noindex'))
        
        return stats