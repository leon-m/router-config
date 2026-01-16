from dataclasses import dataclass

from lib.logging import get_logger
from lib.db_postgresql import PostgreSqlAdapter
from lib.db_adapter import DbAdapter

_log = get_logger(__name__)

def get_db_adapter(connection_string : str) -> DbAdapter:
    parts = connection_string.split(':')
    if parts[0] == 'postgresql':
        return PostgreSqlAdapter(connection_string=connection_string)
    else:
        log.error(f'Database adapter for connection string {connection_string} is not known')

