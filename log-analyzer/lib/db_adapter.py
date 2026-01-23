
from typing import Iterator
from dataclasses import dataclass
from lib.blacklist_model import BlacklistItem
from lib.log_model import LogRecord, RecordType, TCPLogRecord, UDPLogRecord, ICMPLogRecord, OtherLogRecord, IPLogRecord, tuple_to_log
from lib.logging import get_logger
from lib.ipv4 import IPv4Protocol
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
    def __init__(self) -> None:
        self.log = get_logger(__name__)
        self._fetch_phase = None
        self._fetch_result = None
        self._fetch_cycle = { IPv4Protocol.TCP : IPv4Protocol.UDP, IPv4Protocol.UDP : IPv4Protocol.ICMP, IPv4Protocol.ICMP : IPv4Protocol.RESERVED, IPv4Protocol.RESERVED : None }

    def db_name(self) -> str:
        raise NotImplementedError

    def __next__(self) -> LogRecord:
        if self._fetch_result is None:
            raise StopIteration
        try:
            return tuple_to_log(self._fetch_result.__next__())
        except StopIteration:
            self._fetch_phase = self._fetch_cycle[self._fetch_phase]
            if self._fetch_phase is None:
                raise StopIteration
            elif self._fetch_phase == IPv4Protocol.UDP:
                self._fetch_result = self._run_sql(f'SELECT * from v_udp WHERE timestamp > {self._since}')
            elif self._fetch_phase == IPv4Protocol.ICMP:
                self._fetch_result = self._run_sql(f'SELECT * from v_icmp WHERE timestamp > {self._since}')
            else:
                self._fetch_result = self._run_sql(f'SELECT * from v_any WHERE timestamp > {self._since}')
            return self.__next__()

    def __iter__(self) -> Iterator:
        return self

    def fetch(self, since : int) -> Iterator:
        """
            Fetches all log records newer than since EPOCH and returns
            an iterator through the collection.

            The database specific adapters may, but are not expected to override 
            this method. IF they do, however, they should accordingly override
            __next__(), too.
        """
        self._since = since
        self._fetch_result = self._run_sql(f'SELECT * FROM v_tcp WHERE timestamp > {self._since}')
        self._fetch_phase = IPv4Protocol.TCP
        return self

    def log_import(self, records : Iterator):
        """
            Import raw log records into the internal database. The database specific adapters may,
            but are not expected to override this method. The method will use database transactions
            to insert a batch of transactions.

            :param records: Iterator through raw records
            :type records: Iterator
        """

        batch_list = []
        count = 0    

        for record in records:
            batch_list.append(record)
            count += 1
            if count % self._transation_batch_size() == 0:
                self._log_import_batch(batch_list)
                batch_list = [ ]

        if len(batch_list) > 0:
            self._log_import_batch(batch_list)
        self.log.info(f'Imported {count} log records into internal {self.db_name()} database.')

    def get_most_recent_timestamp(self) -> int:
        """
            Returns the EPOCH timestamp of the most recent log record in the archive
            database.        
        """
        try:
            result = self._run_sql('SELECT MAX(timestamp) FROM log_base').__next__()[0]
            return 0 if result is None else int(result)
        
        except StopIteration:
            return 0

    def get_unresolved_geoip(self, nitems : int) -> Iterator:
        return self._run_sql(f"""
            SELECT DISTINCT addr from geoip 
            WHERE resolved = FALSE
            LIMIT {nitems}
        """)

    # Assume that list does not exceed reasonable transaction size - the geoip site has
    # a limit of 100 IP addresses per query which is fine
    def set_geoip_data_from_list(self, data : list[dict[str, str]]) -> None:
        self.log.debug(f'about to update geoip data for {len(data)} IP addresses')
        try:
            self._start_transaction()
            for item in data:
                if item['status'] == 'fail':
                    a = item['query']
                    m = item['message']
                    self.log.warning(f'Query for IP address {a} failed with message: {m}')
                    self._db.set_geoip_data(a, '', '', '', '', '',  '0', '0')
                else:
                    self._set_geoip_data(
                        item['query'],
                        self._sanitize(item['country']), 
                        self._sanitize(item['countryCode']),
                        self._sanitize(item['city']),
                        self._sanitize(item['isp']),
                        self._sanitize(item['org']),
                        item['lat'],
                        item['lon']
                   )

            self._commit_transaction()

        except Exception as ex:
            self._rollback_transaction()
            self.log.error('received exception while updating GeoIP data: {:}'.format(ex))

    def clear_blacklist(self) -> None:
        self.log.debug('About to clear blacklist')
        try:
            self._start_transaction()
            self._run_sql('DELETE FROM blacklist')
            self._commit_transaction()
            self.log.debug('Blacklist cleared')

        except Exception as ex:
            self._rollback_transaction()
            self.log.error('exception while clearing blacklist: {"}'.format(ex))
    
    def insert_into_blacklist(self, addresses : list[str]) -> None:
        if len(addresses) > 0:
            try:
                self._start_transaction()
                sql = [ f'INSERT INTO blacklist (addr) VALUES (\'{addresses[0]}\')' ]
                for addr in addresses[1:]:
                    sql.append(f', (\'{addr}\')')
                sql.append(' ON CONFLICT (addr) DO NOTHING')
                self._run_sql(''.join(sql))

                self._commit_transaction();

            except Exception as ex:
                self.log.error('caught exception :"{:}"'.format(ex))
                self._rollback_transaction()
                raise ex
    
    def remove_from_blacklist(self, addresses: list[str]) -> None:
       if len(addresses) > 0:
            try:
                self._start_transaction()
                sql = [ f'DELETE FROM blacklist WHERE addr IN ( \'{addresses[0]}\'']
                for addr in addresses[1:]:
                    sql.append(f', \'{addr}\'')
                sql.append(')')
                self._run_sql(''.join(sql))
                self._commit_transaction()

            except Exception as ex:
                self.log.error('caught exception :"{:}"'.format(ex))
                self._rollback_transaction()
                raise ex

    # --------------------------------------- INTERNAL IMPLEMENTATIONS -------------------
    # === insertion of new raw log records
    def _sanitize(self, s : str) -> str:
        return s.replace('\'', '\'\'')
    
    def _set_geoip_data(self, addr : str, country : str, c_code : str, city : str, isp : str, org : str, lat : str, lon : str) -> None:
        self._run_sql(f"""
            UPDATE geoip 
            SET resolved = TRUE, country = '{country}', country_code = '{c_code}', 
                city =  '{city}', isp = '{isp}', org = '{org}', lat = {lat}, lon = {lon}
            WHERE resolved = FALSE AND addr = '{addr}'
        """)

    def _log_import_batch(self, batch : list[LogRecord]) -> None:
        self.log.debug(f'importing a batch of {len(batch)} log records')
        rec_id = 0
        try:
            self._start_transaction()
            for rec in batch:
                if rec.type == RecordType.GENERIC:
                    rec_id = self._log_import_other_record(rec)
                elif rec.type == RecordType.NETWORK:
                    if rec.protocol == IPv4Protocol.TCP:
                        rec_id = self._log_import_tcp_record(rec)
                    elif rec.protocol == IPv4Protocol.UDP:
                        rec_id = self._log_import_udp_record(rec)
                    elif rec.protocol == IPv4Protocol.ICMP:
                        rec_id = self._log_import_icmp_record(rec)
                    else:
                        rec_id = self._log_import_any_ip_record(rec)

                    # add non-internal address to geoip table for later lookup
                    if not rec.src_addr.startswith('192.168.'):
                        self._log_insert_into_geo_table(rec_id, rec.src_addr)

            self._commit_transaction()

        except Exception as ex:
            self.log.error(f'while inserting a batch of log records caught an exception: {ex}')
            self._rollback_transaction()

    def _log_insert_into_geo_table(self, rec_id : int, addr : str) -> None:
        self._run_sql(f"""
            INSERT INTO geoip (log_id, addr) VALUES({rec_id}, '{addr}')
        """)                

    def _insert_into_base_table(self, record : LogRecord) -> int:
        """
            Inserts row into log_base table and returns id, the primary key column in
            this table. Note that the database specific adapters must override this
            method owing to different approaches on how to return just inserted value. 
            :rtype: int
        """
        raise NotImplementedError

    def insert_into_ip_table(self, rec_id : int, record : IPLogRecord) -> None:
        self._run_sql(f"""
            INSERT INTO log_ip(log_id, conn_state, protocol, in_itf, blacklisted, src_addr, dst_addr)
                SELECT {rec_id}, '{record.connection_state.value}', {record.protocol.value}, '{record.in_itf}', 
                    EXISTS(SELECT addr FROM blacklist WHERE addr='{record.src_addr}'), '{record.src_addr}', '{record.dst_addr}'
        """)

    def _log_import_other_record(self, record : LogRecord) -> int:
        rec_id = self._insert_into_base_table(record=record)
        self._run_sql(f"""
            INSERT INTO log_messages(log_id, message)
                VALUES ({rec_id}, '{record.message}')
        """)
        return rec_id

    def _log_import_tcp_record(self, record : TCPLogRecord) -> int:
        rec_id = self._insert_into_base_table(record=record)
        self.insert_into_ip_table(rec_id=rec_id, record=record)
        self._run_sql(f"""
            INSERT INTO log_tcp(log_id, tcp_state, src_port, dst_port)
                VALUES ({rec_id}, '{record.tcp_state}', {record.src_port}, {record.dst_port})
        """)
        return rec_id

    def _log_import_udp_record(self, record : UDPLogRecord) -> int:
        rec_id = self._insert_into_base_table(record=record)
        self.insert_into_ip_table(rec_id=rec_id, record=record)
        self._run_sql(f"""
            INSERT INTO log_udp(log_id, src_port, dst_port)
                VALUES ({rec_id}, {record.src_port}, {record.dst_port})
        """)
        return rec_id

    def _log_import_icmp_record(self, record : ICMPLogRecord) -> int:
        rec_id = self._insert_into_base_table(record=record)
        self.insert_into_ip_table(rec_id=rec_id, record=record)
        self._run_sql(f"""
            INSERT INTO log_icmp(log_id, type, code)
                VALUES ({rec_id}, {record.icmp_type}, {record.icmp_code})
        """)
        return rec_id

    def _log_import_any_ip_record(self, record : OtherLogRecord) -> int:
        rec_id = self._insert_into_base_table(record=record)
        self.insert_into_ip_table(rec_id=rec_id, record=record)
        self._run_sql(f"""
            INSERT INTO log_any(log_id)
                VALUES ({rec_id})
        """)
        return rec_id


    def _transation_batch_size(self) -> int:
        """
            Returns optimal number of database operations per transaction. Note that
            that may include inserts into or removal from several tables.

            Database specific adapters may choose to override this method to return
            different number.         

            :return: Optimal number of database operations
            :rtype: int
        """
        return 100
    
    def _start_transaction(self):
        raise NotImplementedError

    def _commit_transaction(self):
        raise NotImplementedError

    def _rollback_transaction(self):
         raise NotImplementedError
    
    def _run_sql(self, sql : str):
         raise NotImplementedError



