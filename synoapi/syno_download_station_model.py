class SynoDownloadStationTaskTransfer(object):
    def __init__(self, **kwargs):
        self.size_downloaded = kwargs.pop('size_downloaded', None)
        self.size_uploaded = kwargs.pop('size_uploaded', None)
        self.speed_download = kwargs.pop('speed_download', None)
        self.speed_upload = kwargs.pop('speed_upload', None)


class SynoDownloadStationAdditional(object):
    def __init__(self, **kwargs):
        self.detail = None
        self.transfer = SynoDownloadStationTaskTransfer(**kwargs.pop('transfer', None))
        self.file = None
        self.tracker = None
        self.peer = None


class SynoDownloadStationTask(object):
    def __init__(self, **kwargs):
        self.id = kwargs.pop('id', None)
        self.type = kwargs.pop('type', None)
        self.username = kwargs.pop('username', None)
        self.title = kwargs.pop('title', None)
        self.size = kwargs.pop('size', None)
        self.status = kwargs.pop('status', None)
        self.status_extra = None
        self.additional = SynoDownloadStationAdditional(**kwargs.pop('additional', None))

    @property
    def progress_percentage(self):
        if self.additional:
            if self.additional.transfer:
                return self.additional.transfer.size_downloaded / self.size * 100.0
        raise Exception('No progress data avaliable for task {}'.format(id))

    @property
    def download_speed(self):
        if self.additional:
            if self.additional.transfer:
                return self.additional.transfer.speed_download
        raise Exception('No speed data avaliable for task {}'.format(id))
