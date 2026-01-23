
import subprocess
from typing import Self
import json
from lib.logging import get_logger
from lib.log_fetcher import LogFetcher
from lib.log_model import json_to_log

class JsonFetcher(LogFetcher):
    _records : None
    _next : None

    def __init__(self, path  : str, since : int):
        self.log = get_logger(__name__)

        # file::<path>
        # sqlite::<user>@<host>:<path>
        # sqlite::<path>
        parts = path.split('::')
        if len(parts) != 2:
            self.log.error('Json path spec must have form <access-method>::<access-data, which {:} isn\'t.'.format(path))
            exit(1)

        cmds = [ ]
        if parts[0] == 'file':
            cmds = ['cat', parts[1]]
            self._path = parts[1]

        elif parts[0] == 'sqlite':
            query = f'SELECT * FROM LOGS WHERE utcsec > {since}'
            aux = parts[1].split(':')
            if len(aux) > 1:
                cmds = [ 'ssh', aux[0], f'sqlite3 --json {aux[1]} "{query}"']
            else:
                cmds = [ 'sqlite3', '--json', parts[1], query]

        else:
            self.log.error('supported access methods are "file" and "sqlite" which "{:}" is not'.format(parts[0]))
            exit(1)

        self.log.info('fetching router log records from the raw store')
        self.log.debug(cmds)
        result = subprocess.run(cmds, stdout=subprocess.PIPE)
        if result.returncode == 0:
            logs = json.loads(result.stdout)
            self.log.info(f'received {len(logs)} raw log records from the source {path}')
        else:
            self.log.error('fetch failed with exit code {:}: {:}'.format(result.returncode, result.stderr))
            exit(result.returncode)

        self._records = logs
        self._next = 0
        
    def __iter__(self):
        return self
    
    def __next__(self):
        if self._next is None or self._next >= len(self._records):
            raise StopIteration
        rec = self._records[self._next]
        self._next += 1
        return json_to_log(int(rec['utcsec']), rec['prog'], rec['msg'])
    
