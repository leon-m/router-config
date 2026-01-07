
import re
from typing import List
from dataclasses import dataclass
from enum import Enum
from lib.logging import get_logger

log = get_logger(__name__)

class LogType(Enum):
    DROP = 1
    BLACKLIST = 2
    OTHER = 3

class IpProtocol(Enum):
    UDP = 1
    TCP = 2
    ICMP = 3

@dataclass
class LogRecord:
    log_type : LogType
    timestamp : int
    topics : List[str]
    message : str


@dataclass
class IPv4Quad:
    src_address : str
    src_port : int
    dst_address : str
    dst_port : int

@dataclass
class BlacklistLogRecord(LogRecord):
    addresses : IPv4Quad


BLACKLISTED = '^#BLACKLISTED: '
def str_to_quad(s : str) -> IPv4Quad:
    """
        Converts 35.203.211.98:53983->95.176.131.108:63473 to IPv4Quad
    """
    parts = s.split('->')
    log.debug('=================== "{:}" -> {:}'.format(s, parts))
    src = parts[0].split(':')
    dst = parts[1].split(':')
    return IPv4Quad(
        src_address=src[0],
        src_port=int(src[1]),
        dst_address=dst[0],
        dst_port=int(dst[1])
    )

def json_list_to_log(json_list : List) -> List[LogRecord]:
    for item in json_list:
        json_to_log(item)
    return None

# input: in:telekom out:(unknown 0), connection-state:new proto TCP (SYN), 35.203.210.46:50491->95.176.131.108:3413, len 44"}
BLACKLIST_TCP_1 = '.+ connection-state:([a-z]+) proto TCP \(([A-Z,]+)\), ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+):([0-9]+)->([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+):([0-9]+)'
#input: in:telekom out:(unknown 0), connection-state:invalid src-mac 10:a3:b8:9b:51:70, proto TCP (RST), 216.58.207.202:443->95.176.131.108:65083, len 40"
BLACKLIST_TCP_INVALID = '.+ connection-state:invalid src-mac ([0-9a-f]+:[0-9a-f]+:[0-9a-f]+:[0-9a-f]+:[0-9a-f]+:[0-9a-f]+).+, ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+):([0-9]+)->([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+):([0-9]+)'
def blacklisted_to_log(msg : str) -> BlacklistLogRecord:
    m = re.match(BLACKLIST_TCP_1, msg)
    if not m is None:
        log.debug('{:} TCP ({:}) {:}:{:} -> {:}:{:}'.format(m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)))
        return None
    m = re.match(BLACKLIST_TCP_INVALID, msg)
    if not m is None:
        log.debug('TCP INVALID [{:}] {:}:{:} -> {:}:{:}'.format(m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)))
        return None
    return None

def json_to_log(json : dict) -> LogRecord:
    mac = None
    proto = None
    addr = None
    message = json['msg']

    if message.startswith('#BLACKLISTED: '):
        record = blacklisted_to_log(message[14:])

    return None