from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass
import redis

if TYPE_CHECKING:
    from logging import Logger


@dataclass(frozen=True)
class CacheServiceSettings:
    redis_host: str
    redis_port: int
    redis_db: str
    redis_password: str
    logger: 'Logger'


class CacheService:
    def __init__(self, cache_service_settings: CacheServiceSettings):
        self.logger = cache_service_settings.logger
        self.rdb = redis.StrictRedis(
            host=cache_service_settings.redis_host,
            port=cache_service_settings.redis_port,
            db=cache_service_settings.redis_db,
            password=cache_service_settings.redis_password,
            decode_responses=True,
            charset='utf-8'
        )
        self.logger.info(
            f'Initialized redis connection at {cache_service_settings.redis_host}:{cache_service_settings.redis_port}, '
            f'db={cache_service_settings.redis_db}'
        )

    def set(self, key: str, value: str) -> None:
        self.rdb.set(key, value)

    def get(self, key: str) -> Optional[str]:
        return self.rdb.get(key)
