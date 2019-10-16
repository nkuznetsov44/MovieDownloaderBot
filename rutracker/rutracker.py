import requests
from bs4 import BeautifulSoup
import urllib
import re
import os
from rutracker.search_result import SearchResult
import logging


class Rutracker:
    REQUEST_TIMEOUT = 10
    allow_redirects = False
    base_page = 'http://rutracker.org/forum/'
    login_page = base_page + 'login.php'
    search_page = base_page + 'tracker.php'
    auth_cookie_name = 'bb_session'
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Connection': 'close',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4',
        'Accept-Encoding': 'gzip, deflate, lzma, sdch',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',
    }

    def __init__(self, username, password, download_folder, proxies=None, cookies=None):
        self.log = logging.getLogger(__name__)
        self.logged_in = False
        self.movie_categories = None
        self.download_folder = download_folder
        self.post_data = {
            'login_username': username,
            'login_password': password,
            'login': 'вход',
        }
        if proxies:
            self.proxies = proxies
        else:
            self.proxies = None
        if cookies is None:
            self.cookies = {}
        else:
            self.cookies = cookies

    def login(self):
        r_kwargs = {
            'allow_redirects': self.allow_redirects,
            'headers': self.headers,
            'timeout': self.REQUEST_TIMEOUT,
        }
        if self.cookies is not None:
            r_kwargs['cookies'] = self.cookies
        response = requests.post(self.login_page, data=self.post_data, proxies=self.proxies, **r_kwargs)
        if self.auth_cookie_name in response.cookies:
            self.cookies = response.cookies
            self.logged_in = True

    def _parse_movie_categories(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        cats = soup.find('optgroup', {'label': re.compile(r'.Кино, Видео и ТВ')})
        self.movie_categories = [cat.contents[0].strip().replace('|- ', '') for cat in cats.find_all('option')]

    def search(self, search_text):
        url = self.search_page + '?' + urllib.parse.urlencode({'nm': search_text})
        if not self.logged_in:
            raise Exception('Not logged in')
        response = requests.get(url, cookies=self.cookies, proxies=self.proxies)
        search_result = SearchResult(response.text)
        if self.movie_categories is None:
            self._parse_movie_categories(response.text)
        return search_result.filter(lambda tor: tor.forum in self.movie_categories and tor.seeds > 0)

    def download(self, torrent_id):
        url = self.base_page + 'dl.php?t={}'.format(torrent_id)
        r = requests.get(url, allow_redirects=True, proxies=self.proxies, cookies=self.cookies)
        self.log.info('Downloading {}'.format(url))
        open(os.path.join(self.download_folder, torrent_id + '.torrent'), 'wb').write(r.content)
