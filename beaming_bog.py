import requests
from bs4 import BeautifulSoup
import csv
from urllib.parse import urlparse, urljoin
import re
from requests.exceptions import RequestException

def normalize_url(url):
    # Lowercasing the URL and stripping trailing slashes
    return url.lower().rstrip('/')

def get_domain(url):
    parsed_url = urlparse(url)
    domain = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_url)
    return domain

def sanitise_url(url):
    if not re.match(r'http(s?)://', url):
        for prefix in ['https://', 'http://']:
            try_url = prefix + url
            try:
                response = requests.get(try_url)
                response.raise_for_status()
                return normalize_url(try_url)
            except (RequestException, Exception):
                continue
    else:
        try:
            response = requests.get(url)
            response.raise_for_status()
            return normalize_url(url)
        except (RequestException, Exception):
            try_url = re.sub(r'http(s?)://', r'http\1://www.', url)
            if requests.get(try_url).status_code == 200:
                return normalize_url(try_url)
    raise ValueError(f"Failed to sanitise URL: {url}")

def scrape_page(url, domain):
    try:
        response = requests.get(url)
    except RequestException as e:
        print(f"Failed to retrieve {url}: {e}")
        return None, []

    soup = BeautifulSoup(response.text, 'html.parser')
    
    page_data = {'URL': url}
    
    for h_tag in ['H1', 'H2']:
        tags = [tag.text for tag in soup.find_all(h_tag.lower())]
        for i, tag_text in enumerate(tags, 1):
            page_data[f'{h_tag} - {i}'] = tag_text
    
    page_data.update({
        'Title': soup.title.string if soup.title else '',
        'META Description': soup.find('meta', {'name': 'description'})['content'] if soup.find('meta', {'name': 'description'}) else ''
    })

    links = [normalize_url(urljoin(url, a['href'])) for a in soup.find_all('a', href=True) if not a['href'].startswith('#') and get_domain(urljoin(url, a['href'])) == domain]
    
    return page_data, links


def main():
    input_url = input("Enter the URL: ")
    try:
        start_url = sanitise_url(input_url)
    except ValueError as e:
        print(e)
        return

    domain = get_domain(start_url)
    visited_urls = set()
    to_visit_urls = {start_url}

    all_headers = set(['URL', 'Title', 'META Description'])
    all_rows = []

    while to_visit_urls:
        current_url = to_visit_urls.pop()

        if current_url in visited_urls:
            continue

        page_data, links = scrape_page(current_url, domain)

        if page_data:
            all_headers.update(page_data.keys())
            all_rows.append(page_data)
            print(f"{current_url} ✅")
            
            for link in links:
                if link not in visited_urls:
                    to_visit_urls.add(link)

            visited_urls.add(current_url)

    sanitised_url = re.sub(r'[\\/:*?"<>|\s]', '_', start_url)
    filename = f"{sanitised_url}_scraped_results.csv"

    column_order = ['URL', 'Title'] + sorted([col for col in all_headers if col not in {'URL', 'Title', 'META Description'}]) + ['META Description']

    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=column_order)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

if __name__ == "__main__":
    main()
