from typing import Optional, List, Dict, Any
import requests
from telegramapi.types import Update
from json import JSONDecodeError


class TelegramApiException(Exception):
    def __init__(self, *args, error_code: Optional[int] = None, description: Optional[str] = None):
        super(TelegramApiException, self).__init__(*args)
        self.error_code = error_code
        self.description = description


class Bot:
    def __init__(
        self,
        token: str
    ):
        self.token = token
        self.url = 'https://api.telegram.org/bot' + token + '/'

    @staticmethod
    def _check_response(response: requests.Response) -> Any:
        if response.status_code != requests.codes.ok:
            raise TelegramApiException(
                f'Got status code {response.status_code}: {response.reason}\n{response.text.encode("utf8")}'
            )

        try:
            response_json = response.json()
        except JSONDecodeError as jde:
            raise TelegramApiException(
                f'Got invalid json\n{response.text.encode("utf8")}', jde
            )

        try:
            if not response_json['ok']:
                raise TelegramApiException(
                    error_code=response_json['error_code'],
                    description=response_json['description']
                )
            return response_json['result']
        except KeyError as ke:
            raise TelegramApiException(
                f'Got unexpected json\n{response_json}', ke
            )

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
        result = self._make_request('get_updates', params=params)
        if len(result) > 0:
            return Update.schema.loads(result, many=True)
