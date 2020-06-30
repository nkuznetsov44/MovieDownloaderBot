from typing import Optional, List, Dict, Any, Union, Callable, TypeVar, Generic
from abc import ABC, abstractmethod
import requests
from telegramapi.types import Update, Message, User, CallbackQuery, InlineKeyboardMarkup, ReplyKeyboardMarkup, ParseMode
from json import JSONDecodeError


class TelegramBotException(Exception):
    pass


class TelegramApiException(TelegramBotException):
    def __init__(self, *args, error_code: Optional[int] = None, description: Optional[str] = None) -> None:
        super(TelegramApiException, self).__init__(*args)
        self.error_code = error_code
        self.description = description

    def __repr__(self) -> str:
        return (
            super(TelegramApiException, self).__repr__() +
            f'\nErrorCode: "{self.error_code}"\nDescription: "{self.description}"'
        )

    def __str__(self):
        return self.__repr__()


ChatId = Union[int, str]
ReplyMarkup = Optional[Union[InlineKeyboardMarkup, ReplyKeyboardMarkup]]
MessageHandlerFunc = Callable[['Bot', Message], None]
CallbackQueryHandlerFunc = Callable[['Bot', CallbackQuery], None]


T = TypeVar('T')


class Handler(Generic[T], ABC):
    def __init__(self, handler_func: Callable[['Bot', T], None], **kwargs: Any):
        self.__handler_func = handler_func

    @abstractmethod
    def should_handle(self, obj: T) -> bool:
        """Returns True if an object should be handled by this handler"""

    def handle(self, bot_instance: 'Bot', obj: T) -> None:
        self.__handler_func(bot_instance, obj)


class MessageHandler(Handler[Message]):
    def __init__(self, handler_func: MessageHandlerFunc, commands: Optional[List[str]] = None) -> None:
        super().__init__(handler_func)
        self.__handler_func = handler_func
        self.__commands = commands

    def should_handle(self, message: Message) -> bool:
        return (
            not self.__commands or
            not message.text or
            any(message.text.startswith(f'/{command}') for command in self.__commands)
        )


def message_handler(commands: Optional[List[str]] = None) -> Callable[[MessageHandlerFunc], MessageHandler]:
    def wrapper(handler_func: MessageHandlerFunc) -> MessageHandler:
        return MessageHandler(handler_func, commands=commands)
    return wrapper


class CallbackQueryHandler(Handler[CallbackQuery]):
    def __init__(self, handler_func: CallbackQueryHandlerFunc, callback_query_data: Optional[List[str]] = None) -> None:
        super().__init__(handler_func)
        self.__handler_func = handler_func
        self.__callback_query_data = callback_query_data

    def should_handle(self, callback_query: CallbackQuery) -> bool:
        return (
            not self.__callback_query_data or
            not callback_query.data or
            any(callback_query.data and callback_query.data.startswith(cqd) for cqd in self.__callback_query_data)
        )


class BotMeta(type):
    def __new__(mcs, name, bases, attrs):
        message_handlers = attrs['_message_handlers'] = list()

        # inherit bases handlers
        for base in bases:
            message_handlers.extend(getattr(base, '_message_handlers'))

        for attr in attrs.values():
            if isinstance(attr, MessageHandler):
                message_handlers.append(attr)

        return type.__new__(mcs, name, bases, attrs)


class Bot(metaclass=BotMeta):
    def __init__(
        self,
        token: str
    ) -> None:
        self.token = token
        self.url = 'https://api.telegram.org/bot' + token + '/'
        self.last_update_id = None

    @property
    def message_handlers(self) -> List[Handler[Message]]:
        """This message_handlers property is initialized by metaclass"""
        return getattr(self, '_message_handlers')

    @property
    def callback_query_handlers(self) -> List[Handler[CallbackQuery]]:
        """This callback_query_handlers property is initialized by metaclass"""
        return getattr(self, '_callback_query_handlers')

    def long_polling(self, timeout: int = 30) -> None:
        while 1 == 1:
            offset = None
            if self.last_update_id:
                offset = self.last_update_id + 1
            updates = self.get_updates(offset=offset, timeout=timeout)
            if updates:
                self.handle_updates(updates)

    def handle_updates(self, updates: List[Update]) -> None:
        for update in updates:
            if update.message:
                self.handle_message(update.message)
            elif update.callback_query:
                self.handle_callback_query(update.callback_query)

    def handle_message(self, message: Message) -> None:
        message_was_handled = False
        for handler in self.message_handlers:
            if handler.should_handle(message):
                handler.handle(self, message)
                message_was_handled = True
        if not message_was_handled:
            raise TelegramBotException(
                f'Message {Message} was not handled because no suitable message handler was provided.'
            )

    def handle_callback_query(self, callback_query: CallbackQuery) -> None:
        callback_query_was_handled = False
        for handler in self.callback_query_handlers:
            if handler.should_handle(callback_query):
                handler.handle(self, callback_query)
                callback_query_was_handled = True
        if not callback_query_was_handled:
            raise TelegramBotException(
                f'Callback query {CallbackQuery} was not handled'
                'because no suitable callback query handler was provided.'
            )

    @staticmethod
    def _check_response(response: requests.Response) -> Any:
        if response.status_code != requests.codes.ok:
            error_code = None
            description = None
            try:
                response_json = response.json()
                error_code = response_json['error_code'],
                description = response_json['description']
            except Exception:
                pass
            raise TelegramApiException(
                f'Got status code {response.status_code}: {response.reason}\n{response.text.encode("utf8")}',
                error_code=error_code,
                description=description
            )

        try:
            response_json = response.json()
        except JSONDecodeError as jde:
            raise TelegramApiException(f'Got invalid json\n{response.text.encode("utf8")}', jde)

        try:
            if not response_json['ok']:
                raise TelegramApiException(
                    error_code=response_json['error_code'],
                    description=response_json['description']
                )
            return response_json['result']
        except KeyError as ke:
            raise TelegramApiException(f'Got unexpected json\n{response_json}', ke)

    def _make_request(
        self,
        api_method: str,
        http_method: Optional[str] = 'get',
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        if http_method == 'get':
            response = requests.get(self.url + api_method, params=params)
        elif http_method == 'post':
            response = requests.post(self.url + api_method, data=params)
        else:
            raise TelegramApiException(f'Unsupported http method {http_method}')
        return self._check_response(response)

    def get_me(self) -> User:
        return User.from_dict(self._make_request('getMe'))

    def get_updates(
        self,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        timeout: Optional[int] = None,
        allowed_updates: Optional[List[str]] = None
    ) -> List[Update]:
        params = {
            'offset': offset,
            'limit': limit,
            'timeout': timeout,
            'allowed_updates': allowed_updates
        }
        result = self._make_request('getUpdates', params=params)
        if len(result) > 0:
            updates = Update.schema().load(result, many=True)
            self.last_update_id = updates[-1].update_id
            return updates

    def send_message(
        self,
        chat_id: ChatId,
        text: str,
        parse_mode: Optional[ParseMode] = None,
        disable_web_page_preview: Optional[bool] = None,
        disable_notification: Optional[bool] = None,
        reply_to_message_id: Optional[int] = None,
        reply_markup: ReplyMarkup = None
    ) -> Message:
        params = {
            'chat_id': chat_id,
            'text': text,
            'disable_web_page_preview': disable_web_page_preview,
            'disable_notification': disable_notification,
            'reply_to_message_id': reply_to_message_id,
        }
        if reply_markup:
            params['reply_markup'] = reply_markup.to_dict()
        if parse_mode:
            params['parse_mode'] = parse_mode.value
        result = self._make_request('sendMessage', http_method='post', params=params)
        return Message.from_dict(result)

    def send_chat_action(self, chat_id: ChatId, action: str) -> bool:
        params = {
            'chat_id': chat_id,
            'action': action
        }
        return self._make_request('sendChatAction', params=params)
