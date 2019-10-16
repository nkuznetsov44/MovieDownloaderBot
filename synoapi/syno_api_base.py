import requests
import json


class SynoApiException(Exception):
    common_error_codes = {
        100: 'Unknown error',
        101: 'Invalid parameter',
        102: 'The requested API does not exist',
        103: 'The requested method does not exist',
        104: 'The requested version does not support the functionality',
        105: 'The logged in session does not have permission',
        106: 'Session timeout',
        107: 'Session interrupted by duplicate login'
    }

    def __init__(self, message, error_code):
        self.message = message
        self.error_code = error_code
        self.error_message = self.common_error_codes.get(error_code, None)


class SynoApiBase(object):
    def __init__(self, base_url, cgi_path, version, name, api_error_code=None):
        self.base_url_template = base_url + ('' if base_url[-1] == '/' else '/') + 'webapi/{cgi_path}'
        self.cgi_path = cgi_path
        self.version = version
        self.name = name

    def get_request(self, **params):
        method = params.pop('method')
        params = {
            'api': self.name,
            'version': self.version,
            'method': method,
            **params
        }
        http_resp = requests.get(
            self.base_url_template.format(cgi_path=self.cgi_path),
            params=params)
        resp_data = json.loads(http_resp.text)
        if resp_data['success']:
            return resp_data['data']
        raise SynoApiException('Failed to execute GET request with params = {}'.format(params), resp_data['error']['code'])
