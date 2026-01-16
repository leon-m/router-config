
from typing import Iterator
from dataclasses import dataclass

@dataclass
class Username:
    username : str
    password : str

class DbAdapter:
    """
        This class prescribes the interface for the database adapter for
        particular dabase engine. The methods in this interface are not
        implemented.
    """
    def fetch(self, since : int) -> Iterator:
        """
            Fetches all log records newer than since EPOCH and returns
            an iterator through the collection.
        """
        raise NotImplementedError

    def do_import(self, records : Iterator):
        raise NotImplementedError
    
    def get_most_recent_timestamp(self) -> int:
        """
            Returns the EPOCH timestamp of the most recent log record in the archive
            database.        
        """
        raise NotImplementedError

    def create_schema(self) -> None:
        """
            Creates database schema. Will raise exception if schema already exists. Note that
            the assumption for most adapters is that the dabase already exists and that the
            actual adapter is connect with the user credentials permitting CREATE operations
            in the d atabase.
        """
        raise NotImplementedError

    def get_unresolved_geoip(self, nitems : int) -> Iterator:
        raise NotImplementedError

    def set_geoip_data(self, addr : str, country : str, c_code : str, city : str, isp : str, org : str, lat : str, lon : str) -> None:
        raise NotImplementedError

