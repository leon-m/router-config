
from typing import Iterator
import json
import subprocess
from datetime import datetime
from lib.blacklist_model import Blacklist, BlacklistItem
from lib.logging import get_logger
from lib.db_adapter import DbAdapter

class BlacklistBitwireIt(Blacklist):

    def __init__(self, db : DbAdapter) -> None:
        self.log = get_logger(__name__)
        self.db = db

    def __next__(self) -> BlacklistItem:
        if self.iterator is None:
            raise StopIteration
        
        return self.iterator.__next__()
    
    def __iter__(self) -> Iterator:
        return self
    
    def item_from_json(self, item : dict[str, str]) -> BlacklistItem:
        return BlacklistItem(
            address=item['ipAddress'],
            timestamp=datetime.fromisoformat(item['lastReportedAt'].replace('Z', '+00:00')),
            country=item['countryCode'],
            confidence=int(item['abuseConfidenceScore'])
        )
    
    def run_cmd(self, cmd : list[str], cwd : str, exit_on_error : bool = True) -> subprocess.CompletedProcess[bytes]:
        self.log.debug(f'about to run command {cmd}')
        result = subprocess.run( cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
        self.log.debug(f'command returned exit code {result.returncode}')
        if result.returncode != 0:
            self.log.error(f'command "{cmd}" reported error: {result.stderr}')
            if exit_on_error:
                exit(1)

        return result
    
    def import_all(self, path : str) -> None:
        lines = []
        with open(f'{path}/blacklist2.txt') as fd:
            self.db.clear_blacklist()
            batch = 0
            for line in fd:
                if batch % 100 == 0:
                    self.db.insert_into_blacklist(lines)
                    lines = []

                lines.append(line.strip(' \t\n'))
                batch += 1      

            if len(lines) > 0:
                self.db.insert_into_blacklist(lines)

            self.log.info(f'inserted {batch} IP addresses into the blacklist')

    def insert_in_baches(self, addresses : list[str]) -> None:
        batch_size = 0
        batch_list = [ ]
        for addr in addresses:
            if batch_size % 100 == 0:
                self.db.insert_into_blacklist(batch_list)
                batch_list = []
            batch_list.append(addr)
            batch_size += 1

        if len(batch_list) > 0:
            self.db.remove_from_blacklist(batch_list)
        self.log.info(f'Inserted {batch_size} new IP addresses into the blacklist')

    def delete_in_baches(self, addresses : list[str]) -> None:
        batch_size = 0
        batch_list = [ ]
        for addr in addresses:
            if batch_size % 100 == 0:
                self.db.remove_from_blacklist(batch_list)
                batch_list = []
            batch_list.append(addr)
            batch_size += 1
        
        if len(batch_list) > 0:
            self.db.remove_from_blacklist(batch_list)

        self.log.info(f'Deleted {batch_size} IP addresses from the blacklist')
                
    def import_diff(self, path : str):
        remove = []
        insert = []

        # run diff against LAST_IMPORTED tag
        result = self.run_cmd(['git', 'diff', 'LAST_IMPORTED', '--', 'blacklist2.txt'], path)
        lines = result.stdout.decode('utf-8').split('\n')

        # process diffs:
        #    * lines starting with '- ' are those removed in update
        #    * lines starting witk '+ ' are those added to update
        for line in lines:
            if line.startswith('- '):
                remove.append(line[1:].strip())
            elif line.startswith('+ '):
                insert.append(line[1:].strip())
        self.log.debug(f'about to remove {len(remove)} existing addresses and insert {len(insert)} addresses')
        self.delete_in_baches(remove)
        self.insert_in_baches(insert)

    def import_from_file(self, path : str) -> None:
        self.log.info(f'loading blacklist from file {path}')

        # 1. First pull updates from repositoyy
        self.run_cmd(['git', 'pull'], path)

        # 2. next check if LAST_IMPORTED tag exists
        result = self.run_cmd([ 'git', 'tag', '-l', 'LAST_IMPORTED' ], path)
        tag = result.stdout.decode('utf-8').strip(' \n\t')
        if tag != 'LAST_IMPORTED':
            # 3.a No, this is the first time, import everything to blacklist table, clearing it first
            self.import_all(path)
        else:
            # 3.b Yes, calculate diffs ...
            self.import_diff(path)
            #  ... and remove tag so that it can later be set to new commit id
            self.run_cmd([ 'git', 'tag', '-d', 'LAST_IMPORTED' ], path)

        # 4. set tag to the current HEAD
        self.run_cmd([ 'git', 'tag','LAST_IMPORTED' ], path)
    
    def import_from_endpoint(url : str):
        raise NotImplementedError