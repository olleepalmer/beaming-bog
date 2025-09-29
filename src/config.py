"""
Configuration management for Beaming Bog crawler
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import json


@dataclass
class CrawlConfig:
    """Configuration for web crawling"""
    
    # Basic settings
    max_workers: int = 10
    max_depth: int = 10
    max_urls: Optional[int] = None
    
    # Request settings
    timeout: int = 30
    retry_attempts: int = 3
    retry_backoff: float = 1.0
    user_agent: str = "BeamingBog/0.2.0 (Compatible; SEO Crawler)"
    
    # Crawl behavior
    respect_robots_txt: bool = True
    follow_redirects: bool = True
    max_redirects: int = 5
    crawl_delay: float = 0.0
    
    # Content filtering
    excluded_extensions: List[str] = field(default_factory=lambda: [
        'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'docx', 'xlsx', 'zip', 'rar',
        'mp3', 'mp4', 'avi', 'mov', 'wmv', 'flv', 'swf', 'ico', 'svg'
    ])
    excluded_patterns: List[str] = field(default_factory=lambda: [
        'cart', 'search', 'terms-of-service', 'privacy-policy'
    ])
    
    # Parsing settings
    extract_headers: List[str] = field(default_factory=lambda: ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    extract_meta_tags: bool = True
    extract_canonical: bool = True
    extract_robots_meta: bool = True
    extract_open_graph: bool = True
    extract_twitter_cards: bool = True
    extract_structured_data: bool = False
    
    # Export settings
    export_format: str = 'csv'
    output_directory: str = '.'
    
    @classmethod
    def from_file(cls, filepath: str) -> 'CrawlConfig':
        """Load configuration from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls(**data)
    
    def to_file(self, filepath: str) -> None:
        """Save configuration to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.__dict__, f, indent=2, default=str)
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        if self.max_workers < 1:
            issues.append("max_workers must be at least 1")
        if self.max_workers > 50:
            issues.append("max_workers should not exceed 50 for stability")
            
        if self.timeout < 1:
            issues.append("timeout must be at least 1 second")
            
        if self.retry_attempts < 0:
            issues.append("retry_attempts cannot be negative")
            
        if self.max_depth < 0:
            issues.append("max_depth cannot be negative")
            
        if self.crawl_delay < 0:
            issues.append("crawl_delay cannot be negative")
            
        return issues


@dataclass
class ResponseMetrics:
    """Metrics collected for each response"""
    url: str
    final_url: str
    status_code: int
    response_time_ms: float
    page_size_bytes: int
    redirect_count: int
    redirect_chain: List[str] = field(default_factory=list)
    content_type: str = ''
    encoding: str = ''
    headers: Dict[str, str] = field(default_factory=dict)