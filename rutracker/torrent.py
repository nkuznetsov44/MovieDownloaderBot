class Torrent:
    RIP_TYPE_PRIORITY = {
        'CamRip': 0,
        'SatRip': 0,
        'VHSRip': 0,
        'DSRip': 0,
        'LDRip': 1,
        'TVRip': 1,
        'TeleCine': 1,
        'TeleSynch': 1,
        'DVD9': 2,
        'DVD5': 2,
        'DVDRip': 2,
        'WEB-DL': 3,
        'WEB-DLRip': 3,
        'WEBRip': 3,
        'WEB': 3,
        'BDRip-AVC': 4,
        'BDRip': 4,
        'HD-DVDRip': 4,
        'HDDVDRip': 4,
        'HDTVRip': 4,
        'HDTV': 4,
        'HDRip': 4,
        'IPTV-Rip': 4,
        'iTunes': 4,
        'BDRemux': 5,
        'DVDRemux': 5,
        'Blu-ray': 5
    }

    QUALITY_PRIORITY = {
        '2160p': 10,
        '1080p': 9,
        '1080i': 8,
        '720p': 7,
        '480p': 6,
    }

    SOUNDTRACK_PRIORITY = {
        'AVO': 0,
        'SVO': 1,
        'DVO': 2,
        'MVO': 3,
        'DUB': 4
    }

    def __init__(self, **kwargs):
        self.title = kwargs.get('title')
        self.size = kwargs.get('size')
        self.seeds = kwargs.get('seeds')
        self.leech = kwargs.get('leech')
        self.forum = kwargs.get('forum')
        self.link = kwargs.get('link')
        self.movie_title = self._find_movie_title(self.title)
        self.soundtrack = self._find_soundtrack(self.title)
        self.quality = self._find_quality(self.title)
        self.rip_type = self._find_rip_type(self.title)

    @staticmethod
    def _find_movie_title(title):
        return title.split('(')[0].strip()

    @staticmethod
    def _find_soundtrack(title):
        found_soundtracks = list(filter(lambda sp: sp.lower() in title.lower(), Torrent.SOUNDTRACK_PRIORITY.keys()))
        if found_soundtracks:
            # returning st with the most priority
            return sorted(found_soundtracks, key=Torrent.SOUNDTRACK_PRIORITY.get, reverse=True)[-1]
        return None

    @staticmethod
    def _find_quality(title):
        for q in Torrent.QUALITY_PRIORITY.keys():
            if q.lower() in title.lower():
                return q
        return None

    @staticmethod
    def _find_rip_type(title):
        for rt in Torrent.RIP_TYPE_PRIORITY.keys():
            if rt.lower() in title.lower():
                return rt
        return None

    def to_dict(self):
        return {'title': self.title,
                'movie_title': self.movie_title,
                'size': self.size,
                'seeds': self.seeds,
                'leech': self.leech,
                'forum': self.forum,
                'link': self.link,
                'soundtrack': self.soundtrack,
                'quality': self.quality,
                'rip_type': self.rip_type}
