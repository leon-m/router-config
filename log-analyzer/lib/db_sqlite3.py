
from typing import Any, Iterator
from datetime import timezone
import sqlite3

from lib.logging import get_logger
from lib.log_model import RecordType
from lib.ipv4 import IPv4Protocol
from lib.db_adapter import DbAdapter
from lib.blacklist_model import BlacklistItem
from lib.log_model import LogRecord
from lib.utils import utc2epoch
class Sqlite3Adapter(DbAdapter):

    def __init__(self, connection_string : str) -> None:
        super().__init__()
        self._INSERT_BATCH_SIZE = 100
        self._DELETE_BATCH_SIZE = 100

        self.log = get_logger(__name__)
        parts = connection_string.split('://')
        if len(parts) != 2:
            self.log.error(f'sqlite3 connection string should be formed as "sqlite3://<path to database file>" which "{connection_string}" is not')
            exit(1)
        self._connection = sqlite3.connect(parts[1])
        self._cursor = self._connection.cursor()

    def db_name(self):
        return "SQLite3"

    def _start_transaction(self):
        self._run_sql('BEGIN DEFERRED TRANSACTION')

    def _commit_transaction(self):
        self._run_sql('COMMIT TRANSACTION')

    def _rollback_transaction(self):
        self._run_sql('ROLLBACK TRANSACTION')
                
    def _run_sql(self, sql: str) -> Any:
        self.log.debug(f'SQL: {sql}')
        return self._cursor.execute(sql)

    def _insert_into_base_table(self, record : LogRecord) -> int:
        self._run_sql(f"""
            INSERT INTO log_base (timestamp, type, channel, severity)
                VALUES ({utc2epoch(record.timestamp)}, {record.type.value}, '{record.channel}', '{record.severity}')
        """)
        return self._cursor.lastrowid



