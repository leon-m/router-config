
from typing import Iterator, Any

from lib.logging import get_logger
from lib.log_fetcher import LogFetcher
from lib.json_fetcher import JsonFetcher
from lib.db_adapter import DbAdapter
from lib.log_model import LogRecord, tuple_to_log

def get_source(source : str, since : int) -> DbAdapter:
    log = get_logger(__name__)
    log.info(f'Will use source connection string {source} to fetch log records')

    parts = source.split('://')
    if len(parts) != 2:
        log.error(f'Source URI must conform to syntax <method>://<method-specific-data>, which "{source}" doesn\'t')

    if parts[0] == 'json':
        return JsonFetcher(path=parts[1], since=since)
    elif parts[0] == 'postgresql':
        from lib.db_postgresql import PostgreSqlAdapter
        return PostgreSqlAdapter(connection_string=source).fetch(since=since)
    elif parts[0] == 'sqlite':
        from lib.db_sqlite3 import Sqlite3Adapter
        return Sqlite3Adapter(connection_string=source).fetch(since=since)

    return None

class PostgreSqlFetcher(LogFetcher):
    _db_access : DbAdapter
    _iterator : Iterator
    _since : int

    def __init__(self, connection_string : str, since : int) -> None:
        from lib.db_postgresql import PostgreSqlAdapter
        self._db_access = PostgreSqlAdapter(connection_string)
        self._since = since
        self._iterator = None

    def __next__(self) -> LogRecord:
        if self._iterator is None:
            self._iterator = self._db_access.fetch(self._since)
        
        record = self._iterator.__next__()
        return tuple_to_log(record=record)
    
    def __iter__(self) -> Iterator:
        return self

class SQLite3Fetcher(LogFetcher):
    _db_access : DbAdapter
    _iterator : Iterator
    _since : int

    def __init__(self, connection_string : str, since : int) -> None:
        from lib.db_sqlite3 import Sqlite3Adapter
        self._db_access = Sqlite3Adapter(connection_string)
        self._since = since
        self._iterator = None

    def __next__(self) -> LogRecord:
        if self._iterator is None:
            self._iterator = self._db_access.fetch(self._since)
        
        record = self._iterator.__next__()
        return tuple_to_log(record=record)
    
    def __iter__(self) -> Iterator:
        return self

