
import re
from typing import List
from dataclasses import dataclass
from enum import Enum
from lib.logging import get_logger
from lib.ipv4 import IPv4Protocol
from lib.utils import epoch2utc, utc2epoch, utc2iso8601

log = get_logger(__name__)

class RecordType(Enum):
    GENERIC = 1
    NETWORK = 2
class ConnectionState(Enum):
    NEW = 'new'
    INVALID = 'invalid'

    def __str__(self):
        return 'N' if self.name == 'NEW' else 'X'
@dataclass
class LogRecord:
    def __init__(self, ts : int, topics : str,  msg : str, typ : RecordType = RecordType.NETWORK, rec_id : int = 0):
        aux = topics.split(',')
        self.id = rec_id
        self.type = typ
        self.channel=aux[0]
        self.severity = aux[1] if len(aux) > 1 else aux[0]
        self.timestamp = epoch2utc(ts)
        self.message =  msg

    def __str__(self) -> str:
        ret = []
        
        ret.append(utc2iso8601(self.timestamp))
        ret.append(f'({utc2epoch(self.timestamp)})')
        ret.append(f'{self.severity: <6s}')
        ret.append(f'{self.channel:<8s}')
        if not self.message is None:
            ret.append(self.message)
        return ' '.join(ret)

class IPLogRecord(LogRecord):
    connection_state : ConnectionState
    protocol : IPv4Protocol
    in_itf   : str
    src_addr : str
    dst_addr : str
    blacklisted : bool

    def __init__(self, 
                 ts : int, 
                 topics : str, 
                 cs : str, 
                 proto : IPv4Protocol, 
                 in_itf : str,
                 src_addr : str,
                 dst_addr : str,
                 rec_id : int = 0,
                 blacklisted : bool = False):
        super().__init__(ts=ts,  topics=topics, msg=None, rec_id=rec_id)
        self.connection_state = ConnectionState(cs)
        self.protocol = proto
        self.in_itf = in_itf
        self.src_addr = src_addr
        self.dst_addr = dst_addr
    
    def __str__(self) -> str:
        return f'{super().__str__():s} {self.in_itf: <10s} {self.connection_state:s}'
class TCPLogRecord(IPLogRecord):
    tcp_state : str
    src_port : int
    dst_port : int

    def __init__(self, 
                 ts : int, 
                 topics : str,  
                 cs : str,
                 tcp_st : str,
                 src_addr : str,
                 src_port : str,
                 dst_addr : str,
                 dst_port : str,
                 in_itf : str, 
                 rec_id : int = 0,
                 blacklisted : bool = False):
        super().__init__(ts=ts, topics=topics, cs=cs, proto=IPv4Protocol.TCP, in_itf=in_itf, src_addr=src_addr, dst_addr=dst_addr, rec_id=rec_id, blacklisted=blacklisted)
        self.tcp_state = tcp_st
        self.src_port = src_port
        self.dst_port = dst_port

    def __str__(self) ->  str:
        src = ':'.join([ self.src_addr, str(self.src_port)])
        dst = ':'.join([ self.dst_addr, str(self.dst_port)])
        return f'{super().__str__():s} TCP {self.tcp_state: <11s} {src: >21s} ===> {dst: <21s}'

class UDPLogRecord(IPLogRecord):
    src_port : int
    dst_port : int

    def __init__(self, 
                 ts : int, 
                 topics : str,  
                 cs : str,
                 src_addr : str,
                 src_port : str,
                 dst_addr : str,
                 dst_port : str,
                 in_itf : str = 'unknown',
                 rec_id : int = 0,
                 blacklisted : bool = False):
        super().__init__(ts=ts, topics=topics, cs=cs, proto=IPv4Protocol.UDP, in_itf=in_itf, src_addr=src_addr, dst_addr=dst_addr, rec_id=rec_id, blacklisted=blacklisted)
        self.src_port =  src_port
        self.dst_port = dst_port

    def __str__(self) ->  str:
        src = ':'.join([ self.src_addr, str(self.src_port)])
        dst = ':'.join([ self.dst_addr, str(self.dst_port)])
        return f'{super().__str__():s} UDP             {src: >21s} ===> {dst: <21s}'

class ICMPLogRecord(IPLogRecord):
    icmp_type : int
    icmp_code : int

    def __init__(self, 
                 ts : int, 
                 topics : str,  
                 cs : str,
                 icmp_type : str,
                 icmp_code : str,
                 src_addr : str,
                 dst_addr : str,
                 in_itf : str = 'unknown', 
                 rec_id : int = 0,
                 blacklisted : bool = False):
        super().__init__(ts=ts, topics=topics, cs=cs, proto=IPv4Protocol.ICMP, in_itf=in_itf, src_addr=src_addr, dst_addr=dst_addr, rec_id=rec_id, blacklisted=blacklisted)
        self.icmp_type = int(icmp_type)
        self.icmp_code = int(icmp_code)

    def __str__(self) ->  str:
        return f'{super().__str__():s} ICMP {self.icmp_type:>2d},{self.icmp_code:<2d}      {self.src_addr: >21s} ===> {self.dst_addr: <21s}'

class OtherLogRecord(IPLogRecord):

    def __init__(self, 
                 ts : int, 
                 topics : str,  
                 cs : str,
                 proto : str,
                 src_addr : str,
                 dst_addr : str,
                 in_itf : str = 'unknown', 
                 rec_id : int = 0,
                 blacklisted : bool = False):
        super().__init__(ts=ts, topics=topics, cs=cs, proto=IPv4Protocol(int(proto)), in_itf=in_itf, src_addr=src_addr, dst_addr=dst_addr, rec_id=rec_id, blacklisted=blacklisted)

    def __str__(self) ->  str:
        return f'{super().__str__():s} {self.protocol: <10s}      {str(self.src_addr): >21s} ===> {str(self.dst_addr): <21s}'

# input: in:telekom out:(unknown 0), connection-state:new proto TCP (SYN), 35.203.210.46:50491->95.176.131.108:3413, len 44"}
# input: in:telekom out:(unknown 0), connection-state:invalid src-mac 10:a3:b8:9b:51:70, proto TCP (RST), 216.58.207.202:443->95.176.131.108:65083, len 40"
LOG_MESSAGE_TCP = '.+in:([a-zA-Z0-9_-]+).+connection-state:([a-z]+).* proto TCP \\(([A-Z,]+)\\), ([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+):([0-9]+)->([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+):([0-9]+)'
# input: in:telekom out:(unknown 0), connection-state:new src-mac 10:a3:b8:9b:51:70, proto UDP, 17.253.56.203:443->95.176.131.108:59387, len 66
LOG_MESSAGE_UDP = '.+in:([a-zA-Z0-9_-]+).+ connection-state:([a-z]+) src-mac.+, proto UDP, ([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+):([0-9]+)->([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+):([0-9]+)'
# input: in:telekom out:(unknown 0), connection-state:new src-mac 10:a3:b8:9b:51:70, proto ICMP (type 8, code 0), 38.110.42.253->95.176.131.108
LOG_MESSAGE_ICMP = '.+in:([a-zA-Z0-9_-]+).+ connection-state:([a-z]+) src-mac.+, proto ICMP \\(type ([0-9]+). code ([0-9]+)\\), ([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+)->([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+)'
# input: in:telekom out:(unknown 0), connection-state:new src-mac 10:a3:b8:9b:51:70, proto ICMP (type 8, code 0), 38.110.42.253->95.176.131.108
LOG_MESSAGE_OTHER = '.+in:([a-zA-Z0-9_-]+).+ connection-state:([a-z]+) src-mac.+, proto ([0-9]+), ([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+)->([0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+)'

def json_to_log(rec : dict[str, str]) -> LogRecord:
    message = rec['msg']
    if message.startswith('#BLACKLISTED: '):
        msg = message[15:]
    elif message.startswith('!invalid: '):
        msg = message[10:]
    else:
        return LogRecord(int(rec['utcsec']), rec['prog'], message, RecordType.GENERIC)
    
    m = re.match(LOG_MESSAGE_TCP, msg)
    if not m is None:
        log.debug('{:} TCP ({:}) {:}:{:} -> {:}:{:}'.format(m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)))
        return TCPLogRecord(
            ts=int(rec['utcsec']),
            topics=rec['prog'],
            cs=m.group(2),
            tcp_st=m.group(3),
            src_addr=m.group(4),
            src_port=m.group(5),
            dst_addr=m.group(6),
            dst_port=m.group(7),
            in_itf=m.group(1))

    m = re.match(LOG_MESSAGE_UDP, msg)
    if not m is None:
        log.debug('{:} UDP {:}:{:} -> {:}:{:}'.format(m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)))
        return UDPLogRecord(
            ts=int(rec['utcsec']),
            topics=rec['prog'],
            cs=m.group(2),
            src_addr=m.group(3),
            src_port=m.group(4),
            dst_addr=m.group(5),
            dst_port=m.group(6),
            in_itf=m.group(1))

    m = re.match(LOG_MESSAGE_ICMP, msg)
    if not m is None:
        log.debug('{:} ICMP ({:},{:}) {:} -> {:}'.format(m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)))
        return ICMPLogRecord(
            ts=int(rec['utcsec']),
            topics=rec['prog'],
            cs=m.group(2),
            icmp_type=m.group(3),
            icmp_code=m.group(4),
            src_addr=m.group(5),
            dst_addr=m.group(6),
            in_itf=m.group(1))
    
    m = re.match(LOG_MESSAGE_OTHER, msg)
    if not m is None:
        log.debug('{:} proto {:} {:} -> {:}'.format(m.group(1), m.group(2), m.group(3), m.group(4)))
        return OtherLogRecord(
            ts=int(rec['utcsec']),
            topics=rec['prog'],
            cs=m.group(2),
            proto=m.group(3),
            src_addr=m.group(4),
            dst_addr=m.group(5),
            in_itf=m.group(1))

    log.warning('--- {:}'.format(msg))
    return None


def json_list_to_log(json_list : List) -> List[LogRecord]:
    ret = []
    for item in json_list:
        aux = json_to_log(item)
        if not aux is None:
            ret.append(aux)
    return ret

def tuple_to_log(record : tuple) -> LogRecord:
    proto = IPv4Protocol(record[5])
    if proto == IPv4Protocol.TCP:
        return TCPLogRecord(
            ts=record[2],
            topics=','.join([record[3], record[4]]),
            cs=record[6],
            in_itf=record[7],
            tcp_st=record[8],
            src_addr=record[9],
            src_port=record[10],
            dst_addr=record[11],
            dst_port=record[12],
            rec_id=record[0]
        )
    elif proto == IPv4Protocol.UDP:
        return UDPLogRecord(
            ts=record[2],
            topics=','.join([record[3], record[4]]),
            cs=record[6],
            in_itf=record[7],
            src_addr=record[8],
            src_port=record[9],
            dst_addr=record[10],
            dst_port=record[11],
            rec_id=record[0]
        )
    elif proto == IPv4Protocol.ICMP:
        return ICMPLogRecord(
            ts=record[2],
            topics=','.join([record[3], record[4]]),
            cs=record[6],
            in_itf=record[7],
            icmp_type=record[8],
            icmp_code=record[9],
            src_addr=record[10],
            dst_addr=record[11],
            rec_id=record[0]
        )

    return OtherLogRecord(
        ts=record[2],
        proto=record[5],
        topics=','.join([record[3], record[4]]),
        cs=record[6],
        in_itf=record[7],
        src_addr=record[8],
        dst_addr=record[9],
        rec_id=record[0]
    )
