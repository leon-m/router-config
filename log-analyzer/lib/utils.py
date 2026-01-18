
from datetime import datetime, timezone

def epoch2utc(epoch : int) -> datetime:
    return datetime.fromtimestamp(epoch, timezone.utc)

def utc2epoch(ts : datetime) -> int:
    return int(ts.replace(tzinfo=timezone.utc).timestamp())

def utc2iso8601(ts : datetime) -> str:
    return ts.strftime('%Y-%m-%dT%H:%M:%S')

def epoch2iso8601(epoch : int) -> str:
    return epoch2utc(epoch).strftime('%Y-%m-%dT%H:%M:%S')
