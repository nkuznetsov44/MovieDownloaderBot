from synoapi.syno_api_base import SynoApiException
from synoapi.syno_authenticated_api import SynoAuthenticatedApi
from synoapi.syno_download_station_model import SynoDownloadStationTask


class SynoDownloadStationApiException(SynoApiException):
    api_error_codes = {
        400: 'File upload failed',
        401: 'Max number of tasks reached',
        402: 'Destination denied',
        403: 'Destination does not exist',
        404: 'Invalid task id',
        405: 'Invalid task action',
        406: 'No default destination',
        407: 'Set destination failed',
        408: 'File does not exist'
    }

    def __init__(self, message, error_code):
        super(SynoDownloadStationApiException, self).__init__(message, error_code)
        if not self.error_message:
            self.error_message = self.api_error_codes.get(error_code, None)


class SynoDownloadStationTaskApi(SynoAuthenticatedApi):
    api = 'SYNO.DownloadStation.Task'
    cgi_path = 'DownloadStation/task.cgi'
    version = 2
    session = 'DownloadStation'

    def __init__(self, base_url, user, password):
        super(SynoDownloadStationTaskApi, self).__init__(
            base_url=base_url,
            cgi_path = self.cgi_path,
            version=self.version,
            api=self.api,
            session=self.session,
            user=user,
            password=password)

    def list(self, offset=None, limit=None, additional=None):
        """List download station tasks.

        Args:
            offset (int): Optional. Beginning task on the requested recotd. Default to "0".offset
            limit (int): Optional. Number of records requested. "-1" means to list all tasks. Default to "-1".
            additional (List[str]): Optional. Additional requested info. When an additional option is requested,
                objects will be provided in the specified additional option.

                Possible options include:
                    * detail
                    * transfer
                    * file
                    * tracker
                    * peer
        Returns:
            List[SynoDownloadStationTask]: download station tasks info

        """
        params = { 'offset': offset or 0, 'limit': limit or -1, }
        if additional:
            params['additional'] = ','.join(additional)
        resp_data = self.get_request(method='list', **params)
        return [SynoDownloadStationTask(**t) for t in resp_data['tasks']]

    def get_info(self, task_ids, additional=None):
        """Get tasks info by ids.

        Args:
            task_ids (List[str]): task ids
            additional (List[str]): Optional. Additional requested info. When an additional option is requested,
                objects will be provided in the specified additional option.

                Possible options include:
                    * detail
                    * transfer
                    * file
                    * tracker
                    * peer

        Returns:
            List[SynoDownloadStationTask]: download station tasks info

        """
        params = { 'id': ','.join(task_ids) }
        if additional:
            params['additional'] = ','.join(additional)
        resp_data = self.get_request(method='getinfo', **params)
        return [SynoDownloadStationTask(**t) for t in resp_data['tasks']]

    def delete(self, task_ids, force_complete):
        """Delete tasks by ids.

        Args:
            task_ids (List[str]): task ids
            force_complete (boolean): Delete tasks and force to move uncompleted download files to the destination

        """
        params = { 'id': ','.join(task_ids), 'force_complete': force_complete }
        resp_data = self.get_request(**params)
        errors = {}
        for item in resp_data:
            if item['error'] != 0:
                errors[item['id']] = item['error']
        if errors:
            raise SynoDownloadStationApiException('Failed to delete tasks {}, with errors {}'.format(', '.join(errors.keys()), errors), None)

    def pause(self, task_ids):
        """Pause tasks by ids.

        Args:
            task_ids (List[str]): task ids

        """
        params = { 'id': ','.join(task_ids) }
        resp_data = self.get_request(method='pause', **params)
        errors = {}
        for item in resp_data:
            if item['error'] != 0:
                errors[item['id']] = item['error']
        if errors:
            raise SynoDownloadStationApiException('Failed to pause tasks {}, with errors {}'.format(', '.join(errors.keys()), errors), None)

    def resume(self, task_ids):
        """Resume tasks by ids.

        Args:
            task_ids (List[str]): task ids

        """
        params = { 'id': ','.join(task_ids) }
        resp_data = self.get_request(method='resume', **params)
        errors = {}
        for item in resp_data:
            if item['error'] != 0:
                errors[item['id']] = item['error']
        if errors:
            raise SynoDownloadStationApiException('Failed to resume tasks {}, with errors {}'.format(', '.join(errors.keys()), errors), None)
