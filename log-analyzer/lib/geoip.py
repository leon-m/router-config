
import urllib3
from lib.logging import get_logger
from lib.log_db import DbAdapter
import time

BATCH_SIZE = 100
URL = 'http://ip-api.com/batch'
class GeoipScraper:


    def __init__(self, db : DbAdapter):
        self.log = get_logger(__name__)
        self._db = db
        self._pool = urllib3.PoolManager()

    def scrape_loop(self, iterations : int) -> None:
        try_count = 1
        max_retries = 10
        retry_seconds = 10
        while True:
            try:
                addresses = []
                batch = self._db.get_unresolved_geoip(BATCH_SIZE)
                for addr in batch:
                    self.log.debug(f'Fetching geolocation data for address {addr[0]}')
                    addresses.append(addr[0])
                
                if len(addresses) == 0:
                    return
                
                self.log.info(f'Launching new query to {URL} with a batch of {len(addresses)} addresses, try {try_count}')
                resp = self._pool.request(
                    method='POST', 
                    url=URL,
                    json=addresses)
                rl = int(resp.headers['X-Rl'])
                ttl = int(resp.headers['X-Ttl'])

                self.log.info(f'service responded with code {resp.status}. Have {rl} requests left for next {ttl} seconds.')        
                try_count = 1
        # set_geoip_data(self, addr : str, country : str, c_code : str, city : str, isp : str, org : str, lat : str, lon : str)
                if resp.status == 200:   
                    try:
                        self._db.start_transaction()         
                        for item in resp.json():
                            if item['status'] == 'fail':
                                a = item['query']
                                m = item['message']
                                self.log.warning(f'Query for IP address {a} failed with message: {m}')
                                self._db.set_geoip_data(a, '', '', '', '', '',  '0', '0')
                            else:
                                self._db.set_geoip_data(item['query'], item['country'], item['countryCode'], item['city'], item['isp'], item['org'], item['lat'], item['lon'])
                        self._db.commit_transaction()

                    except Exception as ex:
                        self.log.warning('caught exception whileupdating geoip data: {:}'.format(ex))
                        self._db.rollback_transaction()
                else:
                    self.log.error(f'Response code {resp.status}, will terminate the scrape loop')
                    return
                
                if rl == 0:
                    self.log.warning(f'No queries left withing this minute, must wait {ttl} seconds before proceeding')
                    time.sleep(ttl + 10)

            except Exception as ex:
                self.log.warning(f'Exception caught while try to reach service at {URL}, will retry after {retry_seconds} seconds')
                self.log.info(f'exception was: {ex}')
                if try_count >= max_retries:
                    self.log.error(f'Reached max retires ({max_retries}), cannot proceed')
                    return
                try_count = try_count + 1
                time.sleep(retry_seconds)

