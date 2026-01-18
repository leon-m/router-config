
from typing import Iterator, Any

from lib.logging import get_logger
from lib.log_fetcher import LogFetcher
from lib.json_fetcher import JsonFetcher
from lib.db_adapter import DbAdapter
from lib.log_model import LogRecord, tuple_to_log

def get_source(source : str, since : int) -> LogFetcher:
    log = get_logger(__name__)
    log.info(f'Will use source connection string {source} to fetch log records')

    parts = source.split('://')
    if len(parts) != 2:
        log.error(f'Source URI must conform to syntax <method>://<method-specific-data>, which "{source}" doesn\'t')

    if parts[0] == 'json':
        return JsonFetcher(path=parts[1], since=since)
    elif parts[0] == 'postgresql':
        return PostgreSqlFetcher(connection_string=source, since=since)
    elif parts[0] == 'sqlite3':
        return SQLite3Fetcher(connection_string=source, since=since)

    return None
#    m = re.match('(file|ssh|postgresql)://(.+)', cmdline.source)
#    if m.group(1) in ['file', 'ssh']:
#        if m.group(1) == 'ssh':
#            aux = m.group(2).split(':')
#            return RawLogFetcher(m.group(1), aux[0], aux[1], since)
#        else:
#            return RawLogFetcher(m.group(1), None, m.group(2), since)
#    elif m.group(1) == 'postgresql':
#        return PostgreSqlFetcher(cmdline.source, since)
#    else:
#        log.error('unsupported log fetch method "{:}"'.format(cmdline.method))
#        raise Exception(f'unsuported fetch method {cmdline.method}')  

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

