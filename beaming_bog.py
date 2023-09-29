import requests
from bs4 import BeautifulSoup
import csv
from urllib.parse import urlparse, urljoin
import re

EXCLUDED_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'docx', 'xlsx', 'zip', 'rar']

def normalize_url(url):
    return url.lower().rstrip('/')

def get_domain(url):
    parsed_url = urlparse(url)
    domain = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_url)
    return domain

def sanitise_url(url):
    if not re.match(r'http(s?)://', url):
        url = 'http://' + url
    return normalize_url(url)

def is_pagination_link(link):
    pagination_patterns = [
        r'\?page=', r'\?p=', r'\?pg=', r'\?pagenumber=', r'\?start=', r'\?offset=',
        r'/page/', r'/p/', r'/pages/', r'#page='
    ]
    pattern = '|'.join(pagination_patterns)
    return re.search(pattern, link) is not None

def scrape_page(url, domain):
    try:
        response = requests.get(url)
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
    to_visit_urls = {start_url}
    all_headers = set(['URL', 'Title', 'META Description', 'Status code'])
    all_rows = []

    while to_visit_urls:
        current_url = to_visit_urls.pop()
        visited_urls.add(current_url)

        if is_pagination_link(current_url):
            continue

        page_data, links = scrape_page(current_url, domain)
        if page_data:
            all_headers.update(page_data.keys())
            all_rows.append(page_data)
            print(f"{current_url} ✅")
            
            for link in links:
                if link not in visited_urls:
                    to_visit_urls.add(link)

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
