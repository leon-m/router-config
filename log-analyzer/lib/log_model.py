
import re
from typing import List
from dataclasses import dataclass
from enum import Enum
from lib.logging import get_logger
from datetime import datetime, timezone

log = get_logger(__name__)

class LogType(Enum):
    IP = 1
    OTHER = 3

class IpProtocol(Enum):
    ICMP = 1
    IGMP = 2
    IPinIP = 4
    ST = 5
    TCP = 6
    EGP = 8
    IGP = 9
    UDP  = 17
    RDP = 27
    GRE = 47

class ConnectionState(Enum):
    NEW = 'new'
    INVALID = 'invalid'

class LogRecord:

    def __init__(self, type : LogType, ts : int, topics : str,  msg : str):
        self.log_type = type
        aux = topics.split(',')
        self.channel=aux[0]
        self.severity = aux[1] if len(aux) > 1 else aux[0]
        self.timestamp = datetime.fromtimestamp(ts, timezone.utc)
        self.message =  msg

    def __str__(self) -> str:
        ret = []
        
        ret.append(self.timestamp.strftime('%Y-%m-%dT%H:%M:%S'))
        ret.append(self.severity)
        ret.append(self.channel)
        if not self.message is None:
            ret.append(self.message)
        return ' '.join(ret)

@dataclass
class IpAddress:
    address : str = None
@dataclass
class IPv4Quad:
    src_address : IpAddress
    src_port : int
    dst_address : IpAddress
    dst_port : int

class IPLogRecord(LogRecord):
    connection_state : ConnectionState
    def __init__(self, type : LogType, ts : int, topics : str,  msg : str, cs : ConnectionState, proto : IpProtocol):
        super().__init__(log_type=type, timestamp=ts,  topics=topics, message=msg)
        


@dataclass
class TCPLogRecord(IPLogRecord):
    protocol : IpProtocol
    tcp_state : str
    addresses : IPv4Quad


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

BLACKLISTED = '^#BLACKLISTED: '
# input: in:telekom out:(unknown 0), connection-state:new proto TCP (SYN), 35.203.210.46:50491->95.176.131.108:3413, len 44"}
BLACKLIST_TCP_1 = '.+ connection-state:([a-z]+) proto TCP \\(([A-Z,]+)\\), ([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+):([0-9]+)->([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+):([0-9]+)'
# input: in:telekom out:(unknown 0), connection-state:invalid src-mac 10:a3:b8:9b:51:70, proto TCP (RST), 216.58.207.202:443->95.176.131.108:65083, len 40"
BLACKLIST_TCP_2 = '.+ connection-state:([a-z]+) src-mac.+, proto TCP \\(([A-Z,]+)\\), ([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+):([0-9]+)->([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+):([0-9]+)'
# input: in:telekom out:(unknown 0), connection-state:new src-mac 10:a3:b8:9b:51:70, proto UDP, 17.253.56.203:443->95.176.131.108:59387, len 66
BLACKLIST_UDP = '.+ connection-state:([a-z]+) src-mac.+, proto UDP, ([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+):([0-9]+)->([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+):([0-9]+)'
# input: in:telekom out:(unknown 0), connection-state:new src-mac 10:a3:b8:9b:51:70, proto ICMP (type 8, code 0), 38.110.42.253->95.176.131.108
BLACKLIST_ICMP = '.+ connection-state:([a-z]+) src-mac.+, proto ICMP \\(type ([0-9]+). code ([0-9]+)\\), ([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+)->([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+)'
# input: in:telekom out:(unknown 0), connection-state:new src-mac 10:a3:b8:9b:51:70, proto ICMP (type 8, code 0), 38.110.42.253->95.176.131.108
BLACKLIST_OTHER = '.+ connection-state:([a-z]+) src-mac.+, proto ([0-9]+), ([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+)->([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+)'

def blacklisted_to_log(rec : dict[str, str]) -> LogRecord:
    msg = rec['msg'][15:]
    m = re.match(BLACKLIST_TCP_1, msg)
    if not m is None:
        log.debug('{:} TCP ({:}) {:}:{:} -> {:}:{:}'.format(m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)))
        return LogRecord(type=LogType.IP, ts=int(rec['utcsec']), topics=rec['prog'], msg=msg)
    m = re.match(BLACKLIST_TCP_2, msg)
    if not m is None:
        log.debug('{:} TCP ({:}) {:}:{:} -> {:}:{:}'.format(m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)))
        return None
    m = re.match(BLACKLIST_UDP, msg)
    if not m is None:
        log.debug('{:} UDP {:}:{:} -> {:}:{:}'.format(m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)))
        return None
    m = re.match(BLACKLIST_ICMP, msg)
    if not m is None:
        log.debug('{:} ICMP ({:},{:}) {:} -> {:}'.format(m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)))
        return None
    m = re.match(BLACKLIST_OTHER, msg)
    if not m is None:
        log.debug('{:} proto {:} {:} -> {:}'.format(m.group(1), m.group(2), m.group(3), m.group(4)))
        return None

    log.warning('--- {:}'.format(msg))
    return None

def json_to_log(json : dict) -> LogRecord:
    mac = None
    proto = None
    addr = None
    message = json['msg']
    if message.startswith('#BLACKLISTED: '):
        return blacklisted_to_log(json)

    return None

def json_list_to_log(json_list : List) -> List[LogRecord]:
    ret = []
    for item in json_list:
        aux = json_to_log(item)
        if not aux is None:
            ret.append(aux)
    return ret

