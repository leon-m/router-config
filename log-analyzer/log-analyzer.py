#!/usr/bin/env python3

import argparse
from lib.logging import FMT_CONCISE, get_logger, set_log_level, set_log_file
from lib.log_fetcher import LogFetcher
from lib.source import get_source
from lib.log_db import get_db_adapter
from lib.db_adapter import DbAdapter
from lib.utils import epoch2iso8601
from lib.geoip import GeoipScraper

do_display = True

import textwrap as _textwrap
class MultilineFormatter(argparse.HelpFormatter):
    def _fill_text(self, text, width, indent):
#        text = self._whitespace_matcher.sub(' ', text).strip()
        paragraphs = text.split('|n')
        multiline_text = ''
        for paragraph in paragraphs:
            formatted_paragraph = _textwrap.fill(paragraph, width, initial_indent=indent, subsequent_indent=indent) + '\n'
            multiline_text = multiline_text + formatted_paragraph
        return multiline_text
    
def get_arg_parser(desc : str) -> argparse.ArgumentParser:
    desc = """
This program displays, imports and analyzes log records, primarily for the firawall channel,
produced by the router and stored into the SQLite3 database on NAS. It can fetch log records from
different log record sources:|n|n
    json://file::<path to file>|n
        This source is expected to be JSON file produced by exporting SQLite database into array of
        JSON objects. This source can only be used for 'display' and 'import' commands.|n|n
    json://sqlite::user@host:<path to SQLite database>|n
        This source will use ssh to run the SQLite command that exports the database into array of
        JSON objects and will intercept and parse the output. This source can only be used for 'display' 
        and 'import' commands. Note that the remote system must already have the public key of the calling
        user stored as the authorized keys. Password authentication is not supported.|n|n
    json://sqlite::<path to SQLite database>|n
        Similar to the source using ssh above, but will run sqlite3 command to export log recods on the
        local machone.
    postgresql://<username>:<password>@<hostname>:<port>/<database-name>|n
        This source will read the PostgreSQL database containing already imported log records. 
    sqlite://<path to SQLite databse>|n
        This source will read the SQLite database containing already imported log records. 
    """

    arg_parser = argparse.ArgumentParser(description=desc, formatter_class=MultilineFormatter)
    arg_parser.add_argument('--log-level', action='store', default='INFO', help="Log level threashold", choices=['ERROR', 'WARNING', 'INFO', 'DEBUG'] )
    arg_parser.add_argument('--log-file', action='store', default='none', help='Log file to store JSON formatted logs to [none]')
    arg_parser.add_argument('--source', action='store', default='json://sqlite::root@nas.moja-domena.eu:/volumeUSB1/usbshare/system-logs/192.168.3.1/SYNOSYSLOGDB_192.168.3.1.DB', help='log record source ,see desctiption')

    arg_parser.add_argument('--since-epoch', action='store', default=0, help='fetch records later than time specified as seconds since EPOCH')
    arg_parser.add_argument('--db', action='store', default='postgresql://loguser:no-password@127.0.0.1:5432/logdb', help='Connecti string to use the database of imported logs')
    arg_parser.add_argument('command', nargs='+', choices=['display', 'import', 'create-schema', 'geoip'])
    return arg_parser

def do_display(cmdline: argparse.Namespace) -> None:
    records = get_source(cmdline.source, cmdline.since_epoch)
    for record in records:
        print(record)
    return records

def do_geoip(cmdline : argparse.Namespace) -> None:
    db = get_db_adapter(cmdline.db)
    scraper = GeoipScraper(db)
    scraper.scrape_loop(0)

def do_import(cmdline : argparse.Namespace) -> None:
    if cmdline.source == cmdline.db:
        log.error(f'For import operation both --source and --db cannot be set to the same URL {cmdline.db}')
        exit(1)

    db = get_db_adapter(cmdline.db)
    most_recent = cmdline.since_epoch if cmdline.since_epoch  > 0 else db.get_most_recent_timestamp()

    log.info(f'Will import raw log records newer than {epoch2iso8601(most_recent)} from {cmdline.source}')
    records = get_source(cmdline.source, most_recent)
    db.do_import(records)

def do_create_schema(cmdline : argparse.Namespace) -> None:
    db = get_db_adapter(cmdline.db)
    db.create_schema()

# --- main part
if __name__=="__main__":
    arg_parser = get_arg_parser('MikroTik log file anayzer')
    cmdline = arg_parser.parse_args()

    set_log_file(cmdline.log_file)
    set_log_level(cmdline.log_level)
    log = get_logger(__name__, FMT_CONCISE)

    for command in cmdline.command:
        if command == 'display':
            do_display(cmdline=cmdline)
        elif command == 'import':
            do_import(cmdline)
        elif command == 'create-schema':
            do_create_schema(cmdline)
        elif command == 'geoip':
            do_geoip(cmdline)
        else:
            log.warning(f'unrecognized command {command}, ignored')

