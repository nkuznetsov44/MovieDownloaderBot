from bs4 import BeautifulSoup
import json
from rutracker.torrent import Torrent


class SearchResultPage:
    def __init__(self, torrents, page_number, total_number_of_pages):
        self.torrents = torrents
        self.page_number = page_number
        self.total_number_of_pages = total_number_of_pages
        self.first = None
        self.previous = None
        self.next = None
        self.last = None

    def number(self):
        return self.page_number

    def of(self):
        return self.total_number_of_pages


class SearchResult:
    def __init__(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        tbl = soup.find('table', {'id': 'tor-tbl'})
        self.torrents = []
        for tr in tbl.tbody.find_all('tr'):
            title = tr.find('div', {'class': 't-title'}).a.contents[0]
            size = int(tr.find('td', {'class': 'tor-size'})['data-ts_text'])
            seeds = int(tr.find('b', {'class': 'seedmed'}).contents[0]) if tr.find('b', {'class': 'seedmed'}) else 0
            leech = int(tr.find('td', {'class': 'leechmed'}).contents[0]) if tr.find('td', {'class': 'leechmed'}) else 0
            forum = tr.find('div', {'class': 'f-name'}).a.contents[0]
            link = tr.find('a', {'class': 'tr-dl'})['href'] if tr.find('a', {'class': 'tr-dl'}) else None
            self.torrents.append(Torrent(title=title, size=size, seeds=seeds, leech=leech, forum=forum, link=link))

    @staticmethod
    def _default_sort_key(torrent):
        return (Torrent.SOUNDTRACK_PRIORITY.get(torrent.soundtrack, -1),
                Torrent.RIP_TYPE_PRIORITY.get(torrent.rip_type, -1),
                Torrent.QUALITY_PRIORITY.get(torrent.quality, -1),
                torrent.size)

    def has_results(self):
        return len(self.torrents) > 0

    def sort(self, key=None):
        self.torrents = sorted(self.torrents, key=key or self._default_sort_key, reverse=True)
        return self

    def filter(self, condition):
        self.torrents = list(filter(condition, self.torrents))
        return self

    def to_json(self, indent=2):
        res = [t.to_dict() for t in self.torrents]
        return json.dumps(res, indent=indent, ensure_ascii=False)

    def pages(self, num_on_page=4):
        num_of_torrents = len(self.torrents)

        if num_of_torrents % num_on_page == 0:
            num_of_pages = num_of_torrents // num_on_page
        else:
            num_of_pages = (num_of_torrents // num_on_page) + 1

        if num_of_torrents <= num_on_page:
            first_page = SearchResultPage(self.torrents, 1, 1)
            first_page.first = first_page
            first_page.last = first_page
            return first_page

        first_page = SearchResultPage(self.torrents[0:num_on_page], 1, num_of_pages)
        first_page.first = first_page

        last_page = SearchResultPage(self.torrents[(num_of_pages - 1) * num_on_page: num_of_torrents], num_of_pages, num_of_pages)
        last_page.first = first_page

        first_page.last = last_page
        last_page.first = first_page

        page = first_page
        for i in range(2, num_of_pages):
            page.next = SearchResultPage(self.torrents[(i - 1) * num_on_page: i * num_on_page], i, num_of_pages)
            page.next.first = first_page
            page.next.last = last_page
            page.next.previous = page
            page = page.next

        last_page.previous = page
        return first_page

