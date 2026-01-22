
from typing import Iterator
from lib.blacklist_model import Blacklist
from lib.logging import get_logger
from lib.blacklist_bitwire_ip import BlacklistBitwireIt
from lib.db_adapter import DbAdapter

def import_blacklist(uri : str, db : DbAdapter) -> None:
    log = get_logger(__name__)
    parts = uri.split('://')

    if len(parts) != 2:
        log.error('Blacklist source must contain URI which "{:}" isn\'t'.format(uri))
        exit(1)

    if parts[0] == 'bitwire-it':
        bl = BlacklistBitwireIt(db)
        bl.import_from_file(parts[1])
    else:
        log.error(f'unknown blacxklist uri "{uri}"')
        exit(1)

