
from typing import Any
import json
from lib.logging import get_logger
import subprocess


class LogFetcher:

    def __init__(self, method : str, credentials : str, raw_db  : str):
        self.log = get_logger(__name__)
        if not method in ['none', 'ssh', 'file']:
            self.log.error('unsupported raw log fetch method "{:}"'.format(method))
            exit(1)

        self.cmd = [ ]
        self.method = method
        self.raw_db = raw_db
        self.credentials = credentials

    def fetch(self, since : int = 0) -> Any:
        query = 'select * from logs' if since == 0 else 'select * from logs where utcsec > {:}'.format(since)
        if self.method == 'none':
            cmd = ['sqlite3', '--json', self.raw_db, query]
        elif self.method == 'ssh':
            cmd = ['ssh', self.credentials, 'sqlite3 --json {:} "{:}"'.format(self.raw_db, query)]
        elif self.method == 'file':
            cmd = ['cat', self.raw_db]

        self.log.info('fetching router log records from the raw store')
        self.log.debug(cmd)
        result = subprocess.run(cmd, stdout=subprocess.PIPE)
        if result.returncode == 0:
            logs = json.loads(result.stdout)
            self.log.info('received {:} log records from raw store'.format(len(logs)))
        else:
            self.log.error('fetch failed with exit code {:}: {:}'.format(result.returncode, result.stderr))
            exit(result.returncode)
        return logs
