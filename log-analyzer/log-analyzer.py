import argparse
import subprocess
import json
from logging import Logger
from lib.logging import FMT_CONCISE, get_logger, set_log_level, set_log_file
from lib.log_fetcher import LogFetcher
from lib.log_model import json_list_to_log

do_display = True

def get_arg_parser(desc : str) -> argparse.ArgumentParser:
    arg_parser = argparse.ArgumentParser(description=desc)
    arg_parser.add_argument('--log-level', action='store', default='INFO', help="Log level threashold", choices=['ERROR', 'WARNING', 'INFO', 'DEBUG'] )
    arg_parser.add_argument('--log-file', action='store', default='none', help='Log file to store JSON formatted logs to [logfile.log]')
    arg_parser.add_argument('--fetch-method', action='store', default='none', help='log record fetch method', choices=['none', 'ssh'])
    arg_parser.add_argument('--fetch-login', action='store', default='root@nas.moja-domena.eu', help="ssh login info to fetch logs from")
    arg_parser.add_argument('--fetch-since', action='store', type=int, help='fetch records later than time specified as seconds since EPOCH')
    arg_parser.add_argument('--raw-database', action='store', default='/volumeUSB1/usbshare/system-logs/192.168.3.1/SYNOSYSLOGDB_192.168.3.1.DB', help='Log database on Synology NAS')
    return arg_parser

def fetch_logs_from_storage(log : Logger, credentials : str, db : str, last_timestamp : int) -> subprocess.CompletedProcess:
    cmd = [ 'ssh', credentials, 'sqlite3 --json {:} "select * from logs where utcsec > {:}"'.format(db, last_timestamp) ]
    log.info('fetching logs from storage')
    log.debug('fetch command {:}'.format(' '.join(cmd)))
    result = subprocess.run(cmd, stdout=subprocess.PIPE)
    if result.returncode == 0:
        logs = json.loads(result.stdout)
        log.info('received {:} log records'.format(len(logs)))
    return result



# --- main part
if __name__=="__main__":
    arg_parser = get_arg_parser('MikroTik log file anayzer')
    cmdline = arg_parser.parse_args()

    set_log_file(cmdline.log_file)
    set_log_level(cmdline.log_level)
    log = get_logger(__name__, FMT_CONCISE)

    fetcher = LogFetcher(cmdline.fetch_method, cmdline.fetch_login, cmdline.raw_database)
    result = fetcher.fetch(0 if cmdline.fetch_since is None else cmdline.fetch_since)
    json_list_to_log(result)
#    ret = fetch_logs_from_storage(log, cmdline.log_ssh_login, cmdline.log_database, 1767657450)
#    result = json.loads(ret.stdout)
#    print('received {:} log records'.format(len(result)))
#    print(result[0]['msg'])

