
from typing import Any, Iterator
from datetime import timezone
import psycopg

from lib.logging import get_logger
from lib.log_model import RecordType
from lib.ipv4 import IPv4Protocol
from lib.db_adapter import DbAdapter, Username
from lib.blacklist_model import BlacklistItem
from lib.log_model import LogRecord
from lib.utils import utc2epoch

class PostgreSqlAdapter(DbAdapter):

    def __init__(self, connection_string : str) -> None:
        super().__init__()
        self.log = get_logger(__name__)
        self._connection = psycopg.connect(conninfo=connection_string, autocommit=True)
        self._cursor = self._connection.cursor()

    def _start_transaction(self):
        self._run_sql('START TRANSACTION')

    def _commit_transaction(self):
        self._run_sql('COMMIT TRANSACTION')

    def _rollback_transaction(self):
        self._run_sql('ROLLBACK TRANSACTION')

    def db_name(self):
        return "PostgreSQL"
            
    def _run_sql(self, sql: str) -> Any:
        self.log.debug(f'SQL: {sql}')
        return self._cursor.execute(sql)

    def _init_db(self, cursor: psycopg.Cursor, dbname : str, loguser : Username) -> None:
        self.log.info(f'Database {dbname} to store processed router logs was not found, will create one')
        
        result = cursor.execute(f'SELECT usename FROM pg_catalog.pg_user where usename = \'{loguser.username}\'').fetchone()
        self.log.debug(f'query result: {result}')
        if len(result) < 1:
            self.log.info(f'Database owner {loguser.username} not found, will create new user')
            cursor.execute(f'CREATE USER {loguser.username} WITH ENCRYPTED PASSWORD \'{loguser.password}\'')

        # create new database and make loguser its owner
        self.log.info(f'ceating database "{dbname}"')
        result = cursor.execute(f'CREATE DATABASE {dbname} WITH OWNER={loguser.username}')

    def _insert_into_base_table(self, record : LogRecord) -> int:
        self._run_sql(f"""
            INSERT INTO log_base (timestamp, type, channel, severity)
                VALUES ({utc2epoch(record.timestamp)}, {record.type.value}, '{record.channel}', '{record.severity}')
            RETURNING id
        """)
        return self._cursor.fetchone()[0]

