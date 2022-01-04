from typing import Optional
import re
from message_parsers import IMessageParser, IParsedMessage
from dto.dto import FillDto


number_regexp = re.compile(r'[-+]?[.]?[\d]+(?:,\d\d\d)*[\.]?\d*(?:[eE][-+]?\d+)?')


class FillMessageParser(IMessageParser[FillDto]):
    def parse(self, message_text: str) -> Optional[IParsedMessage[FillDto]]:
        """Returns FillDto on successful parse or None if no fill was found."""
        cnt = 0
        for number_match in re.finditer(number_regexp, message_text):
            cnt += 1
            amount = number_match.group()
            before_phrase = message_text[:number_match.start()].strip()
            after_phrase = message_text[number_match.end():].strip()
            if len(before_phrase) > 0 and len(after_phrase) > 0:
                description = ' '.join([before_phrase, after_phrase])
            else:
                description = before_phrase + after_phrase
        if cnt == 1:
            return IParsedMessage(original_text=message_text, data=FillDto(None, amount, description, None))
        return None
