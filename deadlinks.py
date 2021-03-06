import argparse
import sys
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import requests

class Crawler(object):

    def __init__(self, domain):

        # for now require complete domain searching
        self.domain = 'http://'+urlparse(domain).hostname

        self.urls_crawled = []
        self.broken_links = {}
        self.CRAWLING_LIMIT = 1000

    def sanitize_url(self, url):
        """Return a sanitized/properly formatted url."""

        if url.startswith('http') and self.domain not in url:
            return False

        if url.startswith('mailto:') or url.startswith('tel:'):
            return False

        if self.domain not in url:
            url = self.domain.strip('/') +'/'+ url.strip('/')
        return url

    def links_to_crawl(self, links):
        """Return a list of links to crawl"""

        to_crawl = []

        for link in links:
            clean_link = self.sanitize_url(link)

            if clean_link and clean_link not in self.urls_crawled:
                broken_parent = False

                for path in self.broken_links:

                    if clean_link.startswith(path):
                        broken_parent = True
                        break

                if not broken_parent:
                    to_crawl.append(clean_link)

        return to_crawl


    def get_headers(self, path):
        """Request headers, return status code and content-type"""

        response = requests.head(path)
        status_code = response.status_code

        content_type = response.headers.get('Content-Type')
        return status_code, content_type

    def get_page_links(self, url):
        """Return all links found on given page"""

        page = requests.get(url)
        page_text = page.text
        soup = BeautifulSoup(page_text, 'lxml')

        links = [a['href'] for a in soup.find_all('a', href=True)]
        hrefs = self.links_to_crawl(links)

        return hrefs

    def validate_crawl(self, url):

        url = self.sanitize_url(url)

        if len(self.urls_crawled) >= self.CRAWLING_LIMIT:
            return False

        if not url:
            return False

        if url in self.urls_crawled:
            return False

        return url

    def find_broken_links(self, url, parent=None):
        """Look for broken links on page"""
        sys.stdout.flush()
        print('.', end='')
        url = self.validate_crawl(url)
        if not url:
            return

        self.urls_crawled.append(url)

        status, content_type = self.get_headers(url)

        if status == 200 and content_type.startswith('text/'):

            links = self.get_page_links(url)
            for link in links:

                self.find_broken_links(link, url)
        else:
            if status == 404 and parent:
                self.broken_links.setdefault(parent, [])
                self.broken_links[parent].append(url)

def start_crawl(url):
    """Create crawler instance and perform crawl"""

    crawler = Crawler(url)
    crawler.find_broken_links(crawler.domain)

    if crawler.broken_links:
        for parent_url, deadlinks in crawler.broken_links.items():
            print(parent_url+': ')
            for link in deadlinks:
                print('   ', link)
    else:
        print('No broken links found')


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Find 404s")
    parser.add_argument('domain', help="Domain to crawl")
    args = parser.parse_args()

    start_crawl(args.domain)
