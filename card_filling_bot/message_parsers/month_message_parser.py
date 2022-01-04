from typing import Any, Optional, List
from enum import Enum
import re
from message_parsers import IMessageParser, IParsedMessage


class Month(Enum):
    january = 1
    february = 2
    march = 3
    april = 4
    may = 5
    june = 6
    july = 7
    august = 8
    september = 9
    october = 10
    november = 11
    december = 12


months_regexps = {
    Month.january: r'январ[яеь]',
    Month.february: r'феврал[яеь]',
    Month.march: r'март[ае]?',
    Month.april: r'апрел[яеь]',
    Month.may: r'ма[йяе]',
    Month.june: r'июн[яеь]',
    Month.july: r'июл[яеь]',
    Month.august: r'август[ае]?',
    Month.september: r'сентябр[яеь]',
    Month.october: r'октябр[яеь]',
    Month.november: r'ноябр[яеь]',
    Month.december: r'декабр[яеь]',
}


months_names = {
    Month.january: 'Январь',
    Month.february: 'Февраль',
    Month.march: 'Март',
    Month.april: 'Апрель',
    Month.may: 'Май',
    Month.june: 'Июнь',
    Month.july: 'Июль',
    Month.august: 'Август',
    Month.september: 'Сентябрь',
    Month.october: 'Октябрь',
    Month.november: 'Ноябрь',
    Month.december: 'Декабрь'
}


class MonthMessageParser(IMessageParser[List[Month]]):
    def parse(self, message_text: str) -> Optional[IParsedMessage[List[Month]]]:
        """Returns list of months on successful parse or None if no months were found."""
        results: List[Month] = []
        if message_text:
            for word in message_text.split(' '):
                for month in list(Month):
                    result = re.search(months_regexps[month], word, re.IGNORECASE)
                    if result:
                        results.append(month)
        return IParsedMessage(original_text=message_text, data=results) or None
