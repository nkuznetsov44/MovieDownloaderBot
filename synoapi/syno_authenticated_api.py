from synoapi.syno_api_base import SynoApiBase, SynoApiException
from synoapi.syno_auth_api import SynoApiAuth


SESSION_TIMED_OUT_ERROR_CODE = 106


class SynoAuthenticatedApi(SynoApiBase):
    def __init__(self, **kwargs):
        base_url = kwargs.pop('base_url')
        cgi_path = kwargs.pop('cgi_path')
        version = kwargs.pop('version')
        api = kwargs.pop('api')
        session = kwargs.pop('session')
        user = kwargs.pop('user')
        password = kwargs.pop('password')
        super(SynoAuthenticatedApi, self).__init__(base_url, cgi_path, version, api)
        self._session = session
        self._user = user
        self._password = password
        self._sid = None
        self._auth_api = SynoApiAuth(base_url)

    def _do_get_request(self, **params):
        return super(SynoAuthenticatedApi, self).get_request(_sid=self._sid, **params)

    def _login_and_do_get_request(self, **params):
        self._sid = self._auth_api.login(self._session, self._user, self._password)
        return self._do_get_request(**params)

    def get_request(self, **params):
        if not self._sid:
            return self._login_and_do_get_request(**params)
        try:  # already logged in
            return self._do_get_request(**params)
        except SynoApiException as e:
            if e.error_code == SESSION_TIMED_OUT_ERROR_CODE:
                self._sid = None
                # if session timed out retrying request
                return self._login_and_do_get_request(**params)
            raise

    def logout(self):
        if self._sid:
            self._auth_api.logout(self._session, self._sid)
