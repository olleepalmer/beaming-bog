"""
Export module for various output formats
"""
import csv
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import logging

from .config import ResponseMetrics
from .analyser import PageAnalysis, SEOIssue


logger = logging.getLogger(__name__)


class BaseExporter:
    """Base class for all exporters"""
    
    def export(self, data: List[Dict[str, Any]], filepath: str, **kwargs) -> None:
        """Export data to file"""
        raise NotImplementedError


class CSVExporter(BaseExporter):
    """Export data to CSV format"""
    
    def export(self, data: List[Dict[str, Any]], filepath: str, columns: Optional[List[str]] = None) -> None:
        """
        Export data to CSV file
        
        Args:
            data: List of dictionaries containing crawl data
            filepath: Output file path
            columns: Optional list of columns to include (default: all columns)
        """
        if not data:
            logger.warning("No data to export")
            return
        
        # Determine columns
        if columns is None:
            # Collect all unique keys from all rows
            all_keys = set()
            for row in data:
                all_keys.update(row.keys())
            
            # Define column order
            priority_columns = [
                'url', 'final_url', 'status_code', 'response_time_ms',
                'title', 'title_length', 'meta_description', 'meta_description_length',
                'h1_first', 'h1_count', 'canonical', 'word_count'
            ]
            
            # Order columns: priority first, then alphabetical
            columns = []
            for col in priority_columns:
                if col in all_keys:
                    columns.append(col)
                    all_keys.remove(col)
            
            # Add remaining columns alphabetically
            columns.extend(sorted(all_keys))
        
        # Write CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(data)
        
        logger.info(f"Exported {len(data)} rows to {filepath}")


class JSONExporter(BaseExporter):
    """Export data to JSON format"""
    
    def export(self, data: List[Dict[str, Any]], filepath: str, indent: int = 2) -> None:
        """Export data to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, default=str)
        
        logger.info(f"Exported {len(data)} records to {filepath}")


class HTMLReportExporter(BaseExporter):
    """Export data as HTML report"""
    
    def export(self, crawl_data: Dict[str, Any], filepath: str) -> None:
        """
        Export comprehensive HTML report
        
        Args:
            crawl_data: Dictionary containing all crawl data including:
                - pages: List of crawled pages
                - issues: List of SEO issues
                - statistics: Site statistics
                - duplicates: Duplicate content
            filepath: Output file path
        """
        html = self._generate_html_report(crawl_data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"Exported HTML report to {filepath}")
    
    def _generate_html_report(self, data: Dict[str, Any]) -> str:
        """Generate HTML report content"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Beaming Bog SEO Report - {timestamp}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #4CAF50;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .stat-label {{
            color: #666;
            font-size: 14px;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th {{
            background: #4CAF50;
            color: white;
            padding: 10px;
            text-align: left;
        }}
        td {{
            padding: 8px;
            border-bottom: 1px solid #ddd;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
        .severity-error {{
            color: #d32f2f;
            font-weight: bold;
        }}
        .severity-warning {{
            color: #f57c00;
            font-weight: bold;
        }}
        .severity-info {{
            color: #1976d2;
        }}
        .issue-card {{
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin: 10px 0;
        }}
        .issue-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .issue-url {{
            color: #666;
            font-size: 12px;
            margin-top: 10px;
        }}
        .recommendation {{
            background: #e8f5e9;
            padding: 10px;
            border-radius: 3px;
            margin-top: 10px;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>💩 Beaming Bog SEO Report</h1>
        <p>Generated: {timestamp}</p>
        
        {self._generate_statistics_section(data.get('statistics', {}))}
        {self._generate_issues_summary(data.get('issues', []))}
        {self._generate_top_issues(data.get('top_issues', []))}
        {self._generate_pages_table(data.get('pages', [])[:50])}  <!-- Limit to 50 for performance -->
    </div>
</body>
</html>"""
        return html
    
    def _generate_statistics_section(self, stats: Dict[str, Any]) -> str:
        """Generate statistics section HTML"""
        if not stats:
            return ""
        
        html = "<h2>📊 Site Statistics</h2><div class='stats-grid'>"
        
        stat_items = [
            ('Total Pages', stats.get('total_pages', 0)),
            ('Avg Response Time', f"{stats.get('avg_response_time_ms', 0):.0f}ms"),
            ('Avg Page Size', f"{stats.get('avg_page_size_bytes', 0) / 1024:.1f}KB"),
            ('Avg Word Count', f"{stats.get('avg_word_count', 0):.0f}"),
            ('Pages with Title', stats.get('pages_with_title', 0)),
            ('Pages with Meta Desc', stats.get('pages_with_meta_description', 0)),
            ('NoIndex Pages', stats.get('noindex_pages', 0)),
            ('Error Pages', stats.get('error_pages', 0))
        ]
        
        for label, value in stat_items:
            html += f"""
            <div class='stat-card'>
                <div class='stat-value'>{value}</div>
                <div class='stat-label'>{label}</div>
            </div>"""
        
        html += "</div>"
        return html
    
    def _generate_issues_summary(self, issues: List[SEOIssue]) -> str:
        """Generate issues summary HTML"""
        if not issues:
            return "<h2>✅ No Major Issues Found</h2>"
        
        # Count issues by severity
        error_count = sum(1 for i in issues if isinstance(i, dict) and i.get('severity') == 'error')
        warning_count = sum(1 for i in issues if isinstance(i, dict) and i.get('severity') == 'warning')
        info_count = sum(1 for i in issues if isinstance(i, dict) and i.get('severity') == 'info')
        
        html = f"""
        <h2>⚠️ Issues Summary</h2>
        <div class='stats-grid'>
            <div class='stat-card'>
                <div class='stat-value severity-error'>{error_count}</div>
                <div class='stat-label'>Errors</div>
            </div>
            <div class='stat-card'>
                <div class='stat-value severity-warning'>{warning_count}</div>
                <div class='stat-label'>Warnings</div>
            </div>
            <div class='stat-card'>
                <div class='stat-value severity-info'>{info_count}</div>
                <div class='stat-label'>Info</div>
            </div>
        </div>"""
        
        return html
    
    def _generate_top_issues(self, issues: List[SEOIssue]) -> str:
        """Generate top issues section HTML"""
        if not issues:
            return ""
        
        html = "<h2>🔍 Top Issues to Fix</h2>"
        
        # Show top 10 issues
        for issue in issues[:10]:
            if isinstance(issue, dict):
                severity = issue.get('severity', 'info')
                html += f"""
                <div class='issue-card'>
                    <div class='issue-header'>
                        <strong>{issue.get('issue', 'Unknown Issue')}</strong>
                        <span class='severity-{severity}'>{severity.upper()}</span>
                    </div>
                    <p>{issue.get('details', '')}</p>
                    {f"<div class='recommendation'>💡 {issue.get('recommendation', '')}</div>" if issue.get('recommendation') else ''}
                    <div class='issue-url'>{issue.get('url', '')}</div>
                </div>"""
        
        return html
    
    def _generate_pages_table(self, pages: List[Dict[str, Any]]) -> str:
        """Generate pages table HTML"""
        if not pages:
            return ""
        
        html = """
        <h2>📄 Crawled Pages</h2>
        <table>
            <thead>
                <tr>
                    <th>URL</th>
                    <th>Status</th>
                    <th>Title</th>
                    <th>Response Time</th>
                    <th>Word Count</th>
                    <th>Issues</th>
                </tr>
            </thead>
            <tbody>"""
        
        for page in pages:
            status = page.get('status_code', 'N/A')
            status_class = 'severity-error' if status >= 400 else ''
            
            html += f"""
                <tr>
                    <td style='word-break: break-all; max-width: 300px;'>{page.get('url', '')}</td>
                    <td class='{status_class}'>{status}</td>
                    <td>{page.get('title', '')[:50]}...</td>
                    <td>{page.get('response_time_ms', 0):.0f}ms</td>
                    <td>{page.get('word_count', 0)}</td>
                    <td>{page.get('issue_count', 0)}</td>
                </tr>"""
        
        html += """
            </tbody>
        </table>"""
        
        return html


class Exporter:
    """Main exporter class that manages different export formats"""
    
    def __init__(self, format: str = 'csv'):
        self.exporters = {
            'csv': CSVExporter(),
            'json': JSONExporter(),
            'html': HTMLReportExporter()
        }
        self.format = format
    
    def export_crawl_data(self, 
                         pages_data: List[Dict[str, Any]],
                         metrics: List[ResponseMetrics],
                         analyses: List[PageAnalysis],
                         site_analysis: Dict[str, Any],
                         filepath: str) -> None:
        """
        Export all crawl data in the specified format
        
        Args:
            pages_data: List of parsed page data
            metrics: List of response metrics
            analyses: List of page analyses
            site_analysis: Site-wide analysis results
            filepath: Output file path (extension will be added based on format)
        """
        
        # Combine all data
        combined_data = []
        for i, page in enumerate(pages_data):
            row = page.copy()
            
            # Add metrics if available
            if i < len(metrics):
                metric = metrics[i]
                row.update({
                    'final_url': metric.final_url,
                    'status_code': metric.status_code,
                    'response_time_ms': metric.response_time_ms,
                    'page_size_bytes': metric.page_size_bytes,
                    'redirect_count': metric.redirect_count
                })
            
            # Add analysis if available
            if i < len(analyses):
                analysis = analyses[i]
                row['seo_score'] = analysis.score
                row['issue_count'] = len(analysis.issues)
                row['has_errors'] = any(i.severity == 'error' for i in analysis.issues)
                row['has_warnings'] = any(i.severity == 'warning' for i in analysis.issues)
            
            combined_data.append(row)
        
        # Determine output filepath with extension
        base_filepath = os.path.splitext(filepath)[0]
        
        if self.format == 'csv':
            output_path = f"{base_filepath}.csv"
            self.exporters['csv'].export(combined_data, output_path)
            
        elif self.format == 'json':
            output_path = f"{base_filepath}.json"
            export_data = {
                'metadata': {
                    'total_pages': len(pages_data),
                    'crawl_date': datetime.now().isoformat()
                },
                'pages': combined_data,
                'site_analysis': site_analysis
            }
            self.exporters['json'].export(export_data, output_path)
            
        elif self.format == 'html':
            output_path = f"{base_filepath}.html"
            
            # Prepare data for HTML report
            all_issues = []
            for analysis in analyses:
                for issue in analysis.issues:
                    all_issues.append({
                        'url': analysis.url,
                        'severity': issue.severity,
                        'category': issue.category,
                        'issue': issue.issue,
                        'details': issue.details,
                        'recommendation': issue.recommendation
                    })
            
            report_data = {
                'pages': combined_data,
                'issues': all_issues,
                'statistics': site_analysis.get('statistics', {}),
                'top_issues': sorted(all_issues, 
                                   key=lambda x: {'error': 0, 'warning': 1, 'info': 2}.get(x['severity'], 3))[:20]
            }
            
            self.exporters['html'].export(report_data, output_path)
        
        else:
            raise ValueError(f"Unsupported export format: {self.format}")
        
        return output_path