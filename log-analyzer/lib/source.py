
from typing import Iterator, Any

from lib.logging import get_logger
from lib.json_fetcher import JsonFetcher
from lib.db_adapter import DbAdapter
from lib.raw_fetcher import RawFetcher

def get_source(source : str, since : int) -> DbAdapter:
    log = get_logger(__name__)
    log.info(f'Will use source connection string {source} to fetch log records')

    parts = source.split('://')
    if len(parts) != 2:
        log.error(f'Source URI must conform to syntax <method>://<method-specific-data>, which "{source}" doesn\'t')
        exit(1)

    if parts[0] == 'json':
        return JsonFetcher(path=parts[1], since=since)
    elif parts[0] == 'postgresql':
        from lib.db_postgresql import PostgreSqlAdapter
        return PostgreSqlAdapter(connection_string=source).fetch(since=since)
    elif parts[0] == 'sqlite':
        from lib.db_sqlite3 import Sqlite3Adapter
        return Sqlite3Adapter(connection_string=parts[1]).fetch(since=since)
    elif parts[0] == 'raw':
        return RawFetcher(connection_string=parts[1], since=since)
    else:
        log.error(f'Source method "{parts[0]}" is not supported')
        exit(1)

    return None

