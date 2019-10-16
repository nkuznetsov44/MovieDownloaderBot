from synoapi.syno_api_base import SynoApiBase, SynoApiException


class SynoApiAuthException(SynoApiException):
    api_error_codes = {
        400: 'No such account or incorrect password',
        401: 'Account disabled',
        402: 'Permission denied',
        403: '2-step verification code required',
        404: 'Failed to authenticate 2-step verification code'
    }

    def __init__(self, message, error_code):
        super(SynoApiAuthException, self).__init__(message, error_code)
        if not self.error_message:
            self.error_message = self.api_error_codes.get(error_code, None)


class SynoApiAuth(SynoApiBase):
    api = 'SYNO.API.Auth'
    cgi_path = 'auth.cgi'
    version = 2

    def __init__(self, base_url):
        super(SynoApiAuth, self).__init__(base_url, self.cgi_path, self.version, self.api)

    def login(self, session, account, password):
        """Method to start a new session

        Args:
            session (str): Login session name
            account (str): Login account name
            password (str): Login account password

        Returns:
            str: sid

        """
        params = {
            'session': session,
            'account': account,
            'passwd': password,
            'format': 'sid'
        }
        try:
            resp_data = self.get_request(method='login', **params)
        except SynoApiException as e:
            raise SynoApiAuthException(e.message, e.error_code)
        return resp_data['sid']

    def logout(self, session, sid):
        """Method to logout a session

        Args:
            session (str): Session name to be logged out
            sid (str): Session id to be logged out

        """
        try:
            self.get_request(method='logout', session=session, sid=sid)
        except SynoApiException as e:
            raise SynoApiAuthException(e.message, e.error_code)
