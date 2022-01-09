from typing import Optional, Tuple, TYPE_CHECKING
import re
from dto import CategoryDto, FillDto
from telegramapi.types import Message
from message_parsers import IMessageParser, IParsedMessage
from services.card_fill_service import CardFillService

if TYPE_CHECKING:
    from logging import Logger


class NewCategoryMessageParser(IMessageParser[Tuple[CategoryDto, FillDto]]):
    def __init__(self, card_fill_service: CardFillService, logger: 'Logger') -> None:
        self.card_fill_service = card_fill_service
        self.logger = logger
        self._fill_id_regexp = re.compile(r'(Создание категории для пополнения номер )([0-9]+)(:)')

    def parse(self, message: Message) -> Optional[IParsedMessage[CategoryDto]]:
        if not message.reply_to_message:
            return None
        if not message.reply_to_message.text:
            return None
        if not message.reply_to_message.text.startswith('Создание категории для пополнения номер '):
            return None
        try:
            cat_name, cat_code, cat_proportion = message.text.split(',')
            cat_name = cat_name.strip()
            cat_code = cat_code.strip()
            cat_proportion = float(cat_proportion.strip())
            fill_id = int(self._fill_id_regexp.search(message.reply_to_message.text).group(2))
            fill = self.card_fill_service.get_fill_by_id(fill_id)
            aliases = []
            if fill.description:
                aliases.append(fill.description)
            category = CategoryDto(name=cat_name, code=cat_code, aliases=aliases, proportion=cat_proportion)
            return IParsedMessage(original_message=message, data=(category, fill))
        except Exception:
            self.logger.exception('Ошибка создания категории')
            return None
