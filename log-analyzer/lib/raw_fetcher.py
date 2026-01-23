

from lib.logging import get_logger
from lib.log_fetcher import LogFetcher
from lib.log_model import json_to_log
from lib.db_adapter import DbAdapter
from lib.db_sqlite3 import Sqlite3Adapter
class RawFetcher(LogFetcher):
    _records : None
    _db : DbAdapter

    def __init__(self, connection_string : str, since : int):
        self.log = get_logger(__name__)

        parts = connection_string.split('::')
        if len(parts) != 2:
            self.log.error(f'raw fetcher connection string must have syntax sqlite::<path-to-db-file> which "{connection_string} doesn\'t')
            exit(1)

        self._db = Sqlite3Adapter(parts[1])
        self._records = self._db._run_sql(f"""
            SELECT utcsec, prog, msg FROM logs
            WHERE utcsec > {since}
        """)
        
    def __iter__(self):
        return self
    
    def __next__(self):
        rec = self._records.__next__()
        return json_to_log(rec[0], rec[1], rec[2])
    
