from typing import Iterator
from dataclasses import  dataclass
from datetime import datetime

@dataclass
class BlacklistItem:
    address : str
    timestamp : datetime
    country : str
    confidence : int

class Blacklist:

    def __next__(self) -> BlacklistItem:
        raise NotImplementedError
    
    def __iter__(self) -> Iterator[BlacklistItem]:
        raise NotImplementedError
    
    def import_from_source(self, path : str):
        raise NotImplementedError
