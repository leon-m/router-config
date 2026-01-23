from dataclasses import dataclass

from lib.logging import get_logger
from lib.db_adapter import DbAdapter

_log = get_logger(__name__)

postgresql_adapter_imported = False

def get_db_adapter(connection_string : str) -> DbAdapter:
    parts = connection_string.split('://')
    if len(parts) != 2:
        _log.error(f'The syntax of database connection string is "method://<method-specific>" which "{connection_string}" does not comply to')
        exit(1)

    if parts[0] == 'postgresql':
        from lib.db_postgresql import PostgreSqlAdapter
        return PostgreSqlAdapter(connection_string=connection_string)
    elif parts[0] == 'sqlite':
        from lib.db_sqlite3 import Sqlite3Adapter
        return Sqlite3Adapter(connection_string=parts[1])
    else:
        _log.error(f'Database adapter for connection string {connection_string} is not known')
        exit(1)

