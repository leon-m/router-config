
from time import gmtime
import platform
import logging
import io
#FMT_DEFAULT='%(asctime)s.%(msecs)03dZ %(tnlevelname)-5s %(hostname)s [%(name)-32.32s] [%(filename)24.24s:%(lineno)-4d] - %(message)s'
FMT_CONCISE='%(asctime)s.%(msecs)03dZ %(levelname)-5s %(name).32s:%(filename).16s:%(lineno)d - %(message)s'
FMT_JSON='{"timestamp":"%(asctime)s.%(msecs)03dZ","level":"%(levelname)s","threadName":"%(threadName)s","loggerName":"%(name)s","file":"%(filename)s","line":%(lineno)d,"function":"%(funcName)s","message":"%(message)s"}'
FMT_DEFAULT = FMT_CONCISE

log_level = 'INFO'
log_file = None
logging.basicConfig(level=log_level)
logging.Formatter.converter = gmtime
#logging.getLogger('TestFramework').setLevel('WARNING')
#logging.getLogger('BitcoinRPC').setLevel('WARNING')

logFormatter = logging.Formatter(
    fmt = FMT_DEFAULT,
    datefmt='%Y-%m-%dT%H:%M:%S'
)

class OurFormatter(logging.Formatter):
    def __init(fmt: str | None = None, datefmt: str | None = None, style = "%", validate: bool = True, defaults = None):
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, validate=validate, defaults=defaults)
    
    def format(self, record : logging.LogRecord) -> str:
        fmtd = super().format(record=record)
        msgw=io.StringIO()

        pattern = ',"message":"'
        pos_start = fmtd.find(pattern) + len(pattern)
        pos_end = fmtd.find('"}', pos_start)

        msgw.write(fmtd[ : pos_start])
        for c in fmtd[pos_start : pos_end]:
            match c:
                case '"':
                    msgw.write('\\"')
                case '\n':
                    msgw.write('\\n')
                case '\t':
                    msgw.write('\\t')
                case _:
                    msgw.write(c)
        msgw.write('"}')
        return msgw.getvalue()
class HostnameFilter(logging.Filter):

    def __init__(self, logid):
        self.hostname = logid if logid is not None else platform.node().split('.')[0]
        pass

    def filter(self, record):
        record.hostname = self.hostname
        record.tnlevelname = 'WARN' if record.levelname == 'WARNING' else record.levelname
        return True

loggers = { }

def set_log_level(l):
    global log_level

    logging.getLogger().setLevel(l)
    log_level = l

    for k in loggers.keys():
        loggers[k].setLevel(l)

def set_log_file(file: str) -> None:
    global log_file
    log_file = None if file == 'none' else file

def get_log_level():
    return log_level


def get_logger(name, format = None):
    log = logging.getLogger(name)
    log.propagate = False

    hostname_filter = HostnameFilter(None)

    handler = logging.StreamHandler()
    handler.addFilter(hostname_filter)
    handler.setFormatter(logFormatter if format is None else logging.Formatter(format, datefmt='%Y-%m-%dT%H:%M:%S'))
    log.addHandler(handler)
    log.setLevel(log_level)

    loggers[name] = log

    if log_file != None:
        handler = get_file_handler()
        log.addHandler(handler)

    return log


def get_file_handler():
    hostname_filter = HostnameFilter(None)

    handler = logging.FileHandler(log_file)
    handler.addFilter(hostname_filter)
    handler.setFormatter(OurFormatter(fmt=FMT_JSON,datefmt='%Y-%m-%dT%H:%M:%S'))

    return handler

