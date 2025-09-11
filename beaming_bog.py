import requests
from bs4 import BeautifulSoup
import csv
from urllib.parse import urlparse, urljoin
import re
from typing import Any
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import threading

EXCLUDED_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'docx', 'xlsx', 'zip', 'rar']
type URL = str
type Domain = str

def normalize_url(url) -> URL:
    '''
    Lower case url and remove any white space at the end
    '''

    return url.lower().rstrip('/') 

def get_domain(url) -> Domain:
    '''
    returns scheme://netloc

    Example : https://github.com
    '''

    parsed_url = urlparse(url)
    domain = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_url)
    return domain

def sanitise_url(url:URL) -> URL:

    if not re.match(r'http(s?)://', url):
        url = 'http://' + url
    return normalize_url(url)

def is_pagination_link(url:URL) -> bool:
    '''
    check for pagination
    '''
    pagination_patterns = [
        r'\?page=', r'\?p=', r'\?pg=', r'\?pagenumber=', r'\?start=', r'\?offset=',
        r'/page/', r'/p/', r'/pages/', r'#page='
    ]
    pattern = '|'.join(pagination_patterns)
    return re.search(pattern, url) is not None

def scrape_page(url:URL, domain:Domain) -> tuple[dict[str, Any], list] | None:
    '''
    page_data contains 
    

    - H1, H2 tags

    - Title

    - Meta Description 

    - URL, Status code
    
    links = All a tag links in page

    if there is an error return'll be None, []
    '''

    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
        response = requests.get(url, headers=headers)
        #print(response)
        if 'text/html' not in response.headers.get('Content-Type', ''):
            print(f"Filtered out: {url}")
            return None, []
    except Exception as e:
        print(f"Failed to retrieve {url}: {e}")
        return None, []

    soup = BeautifulSoup(response.text, 'html.parser')
    page_data = {'URL': url, 'Status code': response.status_code}

    for h_tag in ['H1', 'H2']:
        tags = [tag.text.strip() for tag in soup.find_all(h_tag.lower())]
        for i, tag_text in enumerate(tags, 1):
            page_data[f'{h_tag} - {i}'] = tag_text

    page_data.update({
        'Title': soup.title.string.strip() if soup.title else '',
        'META Description': soup.find('meta', {'name': 'description'})['content'].strip() if soup.find('meta', {'name': 'description'}) else ''
    })

    links = []
    # Note that some links will be revealed if you perform a certain action for example logging in as Admin will reveal Admin Dash link 

    for a in soup.find_all('a', href=True):
        link = normalize_url(urljoin(url, a['href']))
        if (get_domain(link) == domain and
                not any(ext in link for ext in EXCLUDED_EXTENSIONS) and
                not any(pattern in link for pattern in ['cart', 'search', 'terms-of-service']) and
                '#' not in link):
            links.append(link)

    return page_data, links

def main():   
    input_url = input("💩 Enter the URL: ")
    try:
        start_url = sanitise_url(input_url)
    except ValueError as e:
        print(e)
        return

    domain = get_domain(start_url)
    visited_urls = set()
    to_visit_urls = Queue()
    to_visit_urls.put(start_url)
    all_headers = set(['URL', 'Title', 'META Description', 'Status code'])
    all_rows = []
    retry_urls = []
    
    # Add thread safety
    visited_urls_lock = threading.Lock()
    all_rows_lock = threading.Lock()
    all_headers_lock = threading.Lock()

    def process_url(current_url):
        if is_pagination_link(current_url):
            return

        page_data, links = scrape_page(current_url, domain)
        if page_data:
            with all_headers_lock:
                all_headers.update(page_data.keys())
            
            if page_data['Status code'] == 429:
                retry_urls.append(current_url)
            else:
                with all_rows_lock:
                    all_rows.append(page_data)
                print(f"{current_url} ✅")
                
                for link in links:
                    with visited_urls_lock:
                        if link not in visited_urls:
                            to_visit_urls.put(link)

    def worker():
        while True:
            try:
                current_url = to_visit_urls.get(timeout=2)  # 2 second timeout
                with visited_urls_lock:
                    if current_url in visited_urls:
                        to_visit_urls.task_done()
                        continue
                    visited_urls.add(current_url)
                
                process_url(current_url)
                to_visit_urls.task_done()
            except Exception:  # Queue.Empty or other exceptions
                break

    # First pass with multiple threads
    with ThreadPoolExecutor(max_workers=10) as executor:
        workers = [executor.submit(worker) for _ in range(10)]
        to_visit_urls.join()

    # Handle retry URLs if any
    if retry_urls:
        print(f"retrying {len(retry_urls)} urls")
        for retry_url in retry_urls:
            to_visit_urls.put(retry_url)
        
        with ThreadPoolExecutor(max_workers=5) as executor:  # Less workers for retries
            workers = [executor.submit(worker) for _ in range(5)]
            to_visit_urls.join()

    # Write the scraped data to CSV
    sanitised_url = re.sub(r'[\\/:*?"<>|\s]', '_', start_url)
    filename = f"{sanitised_url}_scraped_results.csv"

    column_order = ['Status code', 'URL', 'Title', 'META Description'] + \
                   sorted([col for col in all_headers if col not in {'URL', 'Title', 'META Description', 'Status code'}],
                          key=lambda x: (x.split('-')[0], int(x.split('-')[1])) if '-' in x and x.split('-')[0].startswith('H') else (x, 0))

    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=column_order)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

if __name__ == "__main__":
    main()
