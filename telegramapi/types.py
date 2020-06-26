from abc import ABC, abstractmethod, abstractclassmethod
from typing import Optional, List
import json


class JsonSerializable(ABC):
    @abstractmethod
    def to_json(self):
        raise NotImplementedError


class Dictionaryable(ABC):
    @abstractmethod
    def to_dict(self):
        raise NotImplementedError


class JsonDeserializable(ABC):
    @classmethod
    @abstractclassmethod
    def from_json(cls, json_string):
        raise NotImplementedError


class User(JsonSerializable, JsonDeserializable, Dictionaryable):
    def __init__(self, user_id: int, username: Optional[str]):
        self.user_id = user_id
        self.username = username

    def to_dict(self):
        return {
            'id': self.user_id,
            'username': self.username
        }

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_string):
        obj = json.loads(json_string)
        user_id = obj['id']
        username = obj.get('username')
        return cls(user_id, username)


class Chat(JsonSerializable, JsonDeserializable, Dictionaryable):
    def __init__(self, chat_id: int):
        self.chat_id = chat_id

    def to_dict(self):
        return {
            'id': self.chat_id
        }

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_string):
        if json_string is None:
            return None
        obj = json.loads(json_string)
        chat_id = obj['id']
        return cls(chat_id)


class InlineKeyboardButton(JsonSerializable, Dictionaryable):
    def __int__(
        self,
        url: Optional[str],
        callback_data: Optional[str]
    ):
        self.url = url
        self.callback_data = callback_data

    def to_dict(self):
        return {
            'url': self.url,
            'callback_data': self.callback_data
        }

    def to_json(self):
        return json.dumps(self.to_dict())


class InlineKeyboardMarkup(JsonSerializable, Dictionaryable):
    def __init__(self, inline_keyboard: List[List[InlineKeyboardButton]]):
        self.inline_keyboard = inline_keyboard

    def to_dict(self):
        return {
            'inline_keyboard': [[button.to_dict() for button in row] for row in self.inline_keyboard]
        }

    def to_json(self):
        return json.dumps(self.to_dict())


class Message(JsonDeserializable):
    def __init__(
        self,
        message_id: int,
        from_user: Optional[User],
        date: int,
        chat: Chat,
        text: Optional[str],
        reply_markup: Optional[InlineKeyboardMarkup]
    ):
        self.message_id = message_id
        self.from_user = from_user
        self.date = date
        self.chat = chat
        self.text = text
        self.reply_markup = reply_markup

    @classmethod
    def from_json(cls, json_string):
        if json_string is None:
            return None
        obj = json.loads(json_string)
        message_id = obj['message_id']
        from_user = User.from_json(obj.get('from'))
        date = obj['date']
        chat = Chat.from_json(obj['chat'])
        text = obj.get('text')
        reply_markup = None
        return cls(message_id, from_user, date, chat, text, reply_markup)


class CallbackQuery(JsonDeserializable):
    def __init__(
        self,
        callback_query_id: str,
        from_user: User,
        message: Optional[Message],
        data: Optional[str]
    ):
        self.callback_query_id = callback_query_id
        self.from_user = from_user
        self.message = message
        self.data = data

    @classmethod
    def from_json(cls, json_string):
        if json_string is None:
            return None
        obj = json.loads(json_string)
        callback_query_id = obj['id']
        user_from = User.from_json(obj['from'])
        message = Message.from_json(obj.get('message'))
        data = obj.get('data')
        return cls(callback_query_id, user_from, message, data)


class Update(JsonDeserializable):
    def __init__(
        self,
        update_id: int,
        message: Optional[Message],
        callback_query: Optional[CallbackQuery]
    ):
        self.update_id = update_id
        self.message = message
        self.callback_query = callback_query

    @classmethod
    def from_json(cls, json_string):
        if json_string is None:
            return None
        obj = json.loads(json_string)
        update_id = obj['update_id']
        message = Message.from_json(obj.get('message'))
        callback_query = CallbackQuery.from_json(obj.get('callback_query'))
        return cls(update_id, message, callback_query)
