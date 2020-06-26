import json
import requests
from rutracker.rutracker import Rutracker
from synoapi.syno_download_station_api import SynoDownloadStationTaskApi
from telegram_types import Message, CallbackQuery, ReplyMarkup, InlineKeyboardButton
import logging
import math


emoji = {
    'Level Slider': '🎚️',
    'Fast-Forward Button': '⏩',
    'Fast Reverse Button': '⏪',
    'Play Button': '▶️',
    'Reverse Button': '◀️',
    'Movie Camera': '🎥',
    'Film Frames': '🎞️',
    'Studio Microphone': '🎙️',
    'Floppy Disk': '💾',
    'Outbox Tray': '📤',
    'Inbox Tray': '📥',
    'Rocket': '🚀',
    'Trash': '🗑️',
    'Red Circle': '🔴',
    'Green Circle': '🟢',
    'Black Circle': '⚫',
    'Refresh': '🔄',
    'Progress Bar Filled': '▰',
    'Progress Bar Empty': '▱',
}


def _fixed_size_str(data, length):
    if data:
        return str(data) + (' ' * (length - len(str(data))))
    else:
        return ' ' * length


def _sizeof_fmt(num, suffix='B'):
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Y', suffix)


class MovieDownloaderBot:
    username = 'nasMovieDownloaderBot'
    name = 'MovieDownloader'
    results_in_page = 4

    def __init__(self, **kwargs):
        """Movie downloader bot.

        Args:
            telegram_token (str): telegram token
            allowed_users_id (List[int]): telegram allowed users id
            proxy (str): optional, http and https proxy
            rutracker_user (str): rutracker user
            rutracker_password (str): rutracker password
            download_folder (str): synology watched shared folder
            syno_api_url (str): synology api url
            syno_user (str): synology api user
            syno_password (str): synology api password

        """
        telegram_token = kwargs.pop('telegram_token')
        self.allowed_users_id = kwargs.pop('allowed_users_id')
        proxy = kwargs.pop('proxy', None)
        rutracker_user = kwargs.pop('rutracker_user')
        rutracker_password = kwargs.pop('rutracker_password')
        download_folder = kwargs.pop('download_folder')
        syno_api_url = kwargs.pop('syno_api_url')
        syno_user = kwargs.pop('syno_user')
        syno_password = kwargs.pop('syno_password')

        self.log = logging.getLogger(__name__)
        self.url = 'https://api.telegram.org/bot' + telegram_token + '/'
        if proxy:
            self.proxies = {
                'http': proxy,
                'https': proxy
            }
        else:
            self.proxies = None
        self.update_id = None
        self.current_pages = {}
        self.rutracker = Rutracker(rutracker_user, rutracker_password, download_folder, proxies=self.proxies)
        self.syno_download_station = SynoDownloadStationTaskApi(syno_api_url, syno_user, syno_password)
        self.log.info('Starting MovieDownloaderBot')

    @staticmethod
    def _default_serializer(obj):
        return obj.__dict__

    @staticmethod
    def _message_to_send_request_params(message):
        d = {'text': message.text,
             'chat_id': message.chat_id,
             'parse_mode': message.parse_mode}
        if message.reply_markup:
            d['reply_markup'] = json.dumps(message.reply_markup, default=MovieDownloaderBot._default_serializer)
        if message.message_id:
            d['message_id'] = message.message_id
        return d

    @staticmethod
    def _message_from_json(message_j):
        return Message(message_j['text'], chat_id=message_j['chat']['id'], from_user_id=message_j['from']['id'])

    @staticmethod
    def _callback_query_from_json(callback_query_j):
        message = Message(None, chat_id=callback_query_j['message']['chat']['id'],
                          from_user_id=callback_query_j['message']['from']['id'],
                          message_id=callback_query_j['message']['message_id'])
        return CallbackQuery(callback_query_j['data'], message=message)

    def _format_torrent_block(self, torrent):
        return ('{title_emoji} *{title}*```\n\n' +
                '  {rip_type_emoji}{rip_type} {quality_emoji}{quality} {soundtrack_emoji}{soundtrack}\n' +
                '  {size_emoji}{size} {seeds_emoji}{seeds} {leech_emoji}{leech}\n' +
                '  ```/{download_command}\n\n').format(
                    title_emoji=emoji['Movie Camera'],
                    title=torrent.movie_title,
                    rip_type_emoji=emoji['Film Frames'],
                    rip_type=_fixed_size_str(torrent.rip_type, 9),
                    quality_emoji=emoji['Level Slider'],
                    quality=_fixed_size_str(torrent.quality, 5),
                    soundtrack_emoji=emoji['Studio Microphone'],
                    soundtrack=_fixed_size_str(torrent.soundtrack, 3),
                    size_emoji=emoji['Floppy Disk'],
                    size=_fixed_size_str(_sizeof_fmt(torrent.size), 9),
                    seeds_emoji=emoji['Outbox Tray'],
                    seeds=_fixed_size_str(torrent.seeds, 5),
                    leech_emoji=emoji['Inbox Tray'],
                    leech=_fixed_size_str(torrent.leech, 3),
                    download_command=torrent.link.replace('.php?t=', '')
                )

    def _format_torrents(self, torrents):
        return ''.join(map(self._format_torrent_block, torrents))

    def _format_percentage(self, percentage, progress_bar_length=14):
        return (
            emoji['Progress Bar Filled'] * math.floor(percentage * progress_bar_length / 100.0) +
            emoji['Progress Bar Empty'] * math.ceil((100.0 - percentage) * progress_bar_length / 100.0) +
            ' {:.2f}%'.format(percentage)
        )

    def _format_syno_task_block(self, task):
        if task.status == 'downloading':
            bullet_emoji = emoji['Green Circle']
        elif task.status == 'finished':
            bullet_emoji = emoji['Red Circle']
        else:
            bullet_emoji = emoji['Black Circle']
        return (
            (
                '{bullet} *{title}*```\n\n' +
                '  {speed_emoji}{speed} {size_emoji}{size}' +
                '  {percentage}```\n\n'
            ).format(
                bullet=bullet_emoji,
                title=task.title,
                speed_emoji=emoji['Rocket'],
                speed=_fixed_size_str(_sizeof_fmt(task.download_speed) + '/s', 11),
                size_emoji=emoji['Floppy Disk'],
                size=_fixed_size_str(_sizeof_fmt(task.size), 9),
                percentage=self._format_percentage(task.progress_percentage)
            )
        )

    def _format_syno_tasks(self, tasks):
        if tasks:
            return ''.join(map(self._format_syno_task_block, tasks))
        return 'Нет активных задач'

    class CallbackCommand:
        first = 'first'
        previous = 'prev'
        next = 'next'
        last = 'last'
        refresh = 'refresh'

    def search_result_page_to_message(self, search_result_page, as_existing_message=None):
        message_body = self._format_torrents(search_result_page.torrents)
        footer = '```\n\n--------- {} / {} ---------```'.format(search_result_page.number(), search_result_page.of())
        first = InlineKeyboardButton(emoji['Fast Reverse Button'], self.CallbackCommand.first)
        previous = InlineKeyboardButton(emoji['Reverse Button'], self.CallbackCommand.previous)
        next = InlineKeyboardButton(emoji['Play Button'], self.CallbackCommand.next)
        last = InlineKeyboardButton(emoji['Fast-Forward Button'], self.CallbackCommand.last)
        reply_markup = ReplyMarkup(inline_keyboard=[[first, previous, next, last]])
        if as_existing_message:
            as_existing_message.text = message_body + footer
            as_existing_message.reply_markup = reply_markup
            as_existing_message.parse_mode = 'Markdown'
            return as_existing_message
        return Message(message_body + footer, reply_markup=reply_markup, parse_mode='Markdown')

    def syno_tasks_to_message(self, tasks, as_existing_message=None):
        message_body = self._format_syno_tasks(tasks)
        refresh = InlineKeyboardButton(emoji['Refresh'], self.CallbackCommand.refresh)
        reply_markup = ReplyMarkup(inline_keyboard=[[refresh]])
        if as_existing_message:
            as_existing_message.text = message_body
            as_existing_message.reply_markup = reply_markup
            as_existing_message.parse_mode = 'Markdown'
            return as_existing_message
        return Message(message_body, reply_markup=reply_markup, parse_mode='Markdown')

    def _user_is_allowed(self, user_id):
        if self.allowed_users_id:
            return user_id in self.allowed_users_id
        return True

    def get_updates(self, timeout=30, offset=None):
        if offset is None:
            offset = self.update_id
        params = {'timeout': timeout, 'offset': offset}
        response = requests.get(self.url + 'getUpdates', params=params, proxies=self.proxies)
        return response.json()

    def _send_message(self, message):
        if message.chat_id is None:
            raise Exception('Chat id is not specified (message.chat_id is None)')
        self.log.info('Sending:\n{}'.format(json.dumps(message, default=self._default_serializer)))
        response = requests.post(self.url + 'sendMessage',
                                 data=self._message_to_send_request_params(message),
                                 proxies=self.proxies).json()
        if not response['ok']:
            raise Exception('Failed to send message:\n{}, server response is:\n{}'.format(
                json.dumps(message, default=self._default_serializer), response))
        message.message_id = response['result']['message_id']
        return message

    def _edit_message(self, message):
        if message.chat_id is None:
            raise Exception('Chat id is not specified (message.chat_id is None)')
        if message.message_id is None:
            raise Exception('Message id to edit is not specified (message.message_id is None)')
        self.log.info('Editing:\n{}'.format(json.dumps(message, default=self._default_serializer)))
        response = requests.post(self.url + 'editMessageText',
                                 data=self._message_to_send_request_params(message),
                                 proxies=self.proxies).json()
        if not response['ok']:
            raise Exception('Failed to edit message {}, server response is {}'.format(
                json.dumps(message, default=self._default_serializer), response))
        return message

    def _send_or_edit_message(self, message):
        if message.message_id is None:
            return self._send_message(message)
        else:
            return self._edit_message(message)

    def _reply_to(self, to, answer):
        answer.chat_id = to.chat_id
        return self._send_or_edit_message(answer)

    def handle_response(self, response):
        self.log.debug('Handling response:\n{}'.format(response))
        if response['ok']:
            result = response['result']
            if len(result) > 0:
                self.update_id = result[-1]['update_id'] + 1
                for res in result:
                    incoming_message = res.get('message')
                    callback_query = res.get('callback_query')
                    if incoming_message and self._user_is_allowed(incoming_message['from']['id']):
                        self.handle_incoming_message(self._message_from_json(incoming_message))
                    if callback_query:
                        self.handle_callback_query(self._callback_query_from_json(callback_query))

    def handle_incoming_message(self, incoming_message):
        if incoming_message.text.startswith('/'):
            if incoming_message.text == '/start':
                ans = Message('Я ищу фильмы на rutracker.org и качаю их на NAS. Отправь название фильма.')
                self._reply_to(incoming_message, ans)
            elif incoming_message.text == '/help':
                ans = Message('Отправь мне название фильма.')
                self._reply_to(incoming_message, ans)
            elif incoming_message.text == '/status':
                self._handle_download_status(incoming_message)
            elif incoming_message.text.startswith('/dl'):
                self._handle_rutracker_download(incoming_message)
        else:
            self._handle_rutracker_search(incoming_message)

    def _handle_rutracker_download(self, incoming_message):
        if not self.rutracker.logged_in:
            self.rutracker.login()
        filename = self.rutracker.download(incoming_message.text[3:])
        self.log.info('Starting {}'.format(filename))
        self._reply_to(incoming_message, Message('Начал качать. Статус загрузок: /status'))

    def _handle_rutracker_search(self, incoming_message):
        if not self.rutracker.logged_in:
            self.rutracker.login()
        try:
            search_result = self.rutracker.search(incoming_message.text).sort()
        except AttributeError as ae:
            self.log.error('Failed to parse search results', ae)
            return
        if search_result.has_results():
            current_page = search_result.pages(num_on_page=self.results_in_page)
            message = self._reply_to(incoming_message, self.search_result_page_to_message(current_page))
            self.current_pages[(message.chat_id, message.message_id)] = current_page

    def handle_callback_query(self, callback_query):
        message = callback_query.message
        if callback_query.data == self.CallbackCommand.refresh:
            tasks = self.syno_download_station.list(additional=['transfer'])
            self._send_or_edit_message(self.syno_tasks_to_message(tasks, as_existing_message=message))
        else:
            current_page = self.current_pages.get((message.chat_id, message.message_id))
            if current_page:
                if callback_query.data == self.CallbackCommand.next:
                    if current_page.next:
                        self._send_or_edit_message(self.search_result_page_to_message(
                            current_page.next, as_existing_message=message
                        ))
                        self.current_pages[(message.chat_id, message.message_id)] = current_page.next
                elif callback_query.data == self.CallbackCommand.previous:
                    if current_page.previous:
                        self._send_or_edit_message(self.search_result_page_to_message(
                            current_page.previous, as_existing_message=message
                        ))
                        self.current_pages[(message.chat_id, message.message_id)] = current_page.previous
                elif callback_query.data == self.CallbackCommand.last:
                    self._send_or_edit_message(self.search_result_page_to_message(
                        current_page.last, as_existing_message=message
                    ))
                    self.current_pages[(message.chat_id, message.message_id)] = current_page.last
                elif callback_query.data == self.CallbackCommand.first:
                    self._send_or_edit_message(self.search_result_page_to_message(
                        current_page.first, as_existing_message=message
                    ))
                    self.current_pages[(message.chat_id, message.message_id)] = current_page.first
            else:
                self.log.warning('Current page not found for chat_id = {} and message_id = {}'.format(
                    message.chat_id, message.message_id))

    def _handle_download_status(self, incoming_message):
        tasks = self.syno_download_station.list(additional=['transfer'])
        self._reply_to(incoming_message, self.syno_tasks_to_message(tasks))
