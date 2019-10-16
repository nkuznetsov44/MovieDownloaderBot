class InlineKeyboardButton:
    def __init__(self, text, callback_data):
        self.text = text
        self.callback_data = callback_data


class ReplyMarkup:
    def __init__(self, inline_keyboard=None):
        self.inline_keyboard = inline_keyboard


class Message:
    def __init__(self, text, chat_id=None, from_user_id=None, parse_mode=None, reply_markup=None, message_id=None):
        self.text = text
        self.message_id = message_id
        self.chat_id = chat_id
        self.from_user_id = from_user_id
        self.parse_mode = parse_mode
        self.reply_markup = reply_markup


class CallbackQuery:
    def __init__(self, data, message=None):
        self.data = data
        self.message = message
