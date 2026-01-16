from argparse import Namespace
from typing import Self, Iterator, Any
import json
import re
import subprocess

from lib.logging import get_logger
from lib.log_model import json_to_log, tuple_to_log
from lib.log_db import DbAdapter
class LogFetcher:
    def __iter__(self):
        raise NotImplementedError
    def __next(self):
        raise NotImplementedError
    
    @staticmethod
    def get(cmdline : Namespace, since : int) -> Self:
        log = get_logger(__name__)
        log.info(f'Will use source connection string {cmdline.source} to fetch log records')

        m = re.match('(file|ssh|postgresql)://(.+)', cmdline.source)
        if m.group(1) in ['file', 'ssh']:
            if m.group(1) == 'ssh':
                aux = m.group(2).split(':')
                return RawLogFetcher(m.group(1), aux[0], aux[1], since)
            else:
                return RawLogFetcher(m.group(1), None, m.group(2), since)
        elif m.group(1) == 'postgresql':
           return PostgreSqlFetcher(cmdline.source, since)
        else:
           log.error('unsupported log fetch method "{:}"'.format(cmdline.method))
           raise Exception(f'unsuported fetch method {cmdline.method}')  

class PostgreSqlFetcher(LogFetcher):
    _db_access : DbAdapter
    _iterator : Iterator
    _since : int

    def __init__(self, connection_string : str, since : int) -> None:
        self._db_access = DbAdapter.get('postgresql', connection_string, since)
        self._since = since
        self._iterator = None

    def __next__(self) -> Any:
        if self._iterator is None:
            self._iterator = self._db_access.fetch(self._since)
        
        record = self._iterator.__next__()
        return tuple_to_log(record=record)
    
    def __iter__(self):
        return self
class RawLogFetcher(LogFetcher):
    _records : None
    _next : None

    def __init__(self, method : str, credentials : str, raw_db  : str, since : int):
        self.log = get_logger(__name__)
        if not method in ['ssh', 'file']:
            self.log.error('unsupported raw log fetch method "{:}"'.format(method))
            exit(1)

        self.cmd = [ ]
        self.method = method
        self.raw_db = raw_db
        self.credentials = credentials
        self._records = []
        self._next = None

        self._fetch(since)

    def __iter__(self):
        return self
    
    def __next__(self):
        if self._next is None or self._next >= len(self._records):
            raise StopIteration
        rec = self._records[self._next]
        self._next += 1
        return json_to_log(rec)
    
    def _fetch(self, since : int = 0) -> Self:
        query = 'select * from logs' if since == 0 else 'select * from logs where utcsec > {:}'.format(since)
        if self.method == 'none':
            cmd = ['sqlite3', '--json', self.raw_db, query]
        elif self.method == 'ssh':
            cmd = ['ssh', self.credentials, 'sqlite3 --json {:} "{:}"'.format(self.raw_db, f'{query} order by utcsec asc')]
        elif self.method == 'file':
            cmd = ['cat', self.raw_db]

        self.log.info('fetching router log records from the raw store')
        self.log.debug(cmd)
        result = subprocess.run(cmd, stdout=subprocess.PIPE)
        if result.returncode == 0:
            logs = json.loads(result.stdout)
            self.log.info(f'received {len(logs)} raw log records from the {self.method} source ')
        else:
            self.log.error('fetch failed with exit code {:}: {:}'.format(result.returncode, result.stderr))
            exit(result.returncode)

        self._records = logs
        self._next = 0
        return self
