# Beaming Bog 💩 

Beaming Bog is a Python-based web scraping tool inspired by Screaming Frog. 

This is a a simple command line tool that scans a domain and then generates a CSV of the URLs, Title tags, META descriptions and all H1 and H2 tags all links pages within the site.

## Usage

1. Clone this repo ```git clone https://github.com/olleepalmer/beaming-bog```

2. Navigate to the directory and run the script at the command line: ```python beaming-bog.py```

3. It will prompt you for a URL. You can enter just the domain name and it will append `www.` if applicable and try `https://` or if not available, fall back to `http://`.

4. When finished, the script will save a CSV with each page scanned and a column for each element.

## Questions, problems, concerns?

Let me know if you run into any issues! <op@publicbasic.com>