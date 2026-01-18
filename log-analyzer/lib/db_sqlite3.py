
from typing import Any, Iterator
from datetime import timezone
import sqlite3

from lib.logging import get_logger
from lib.log_model import RecordType
from lib.ipv4 import IPv4Protocol
from lib.db_adapter import DbAdapter, Username

class Sqlite3Adapter(DbAdapter):

    def __init__(self, connection_string : str) -> None:
        self.log = get_logger(__name__)
        self._fetch_phase = None
        self._fetch_result = None
        self._fetch_cycle = { IPv4Protocol.TCP : IPv4Protocol.UDP, IPv4Protocol.UDP : IPv4Protocol.ICMP, IPv4Protocol.ICMP : IPv4Protocol.RESERVED, IPv4Protocol.RESERVED : None }
        self._since = 0

        parts = connection_string.split('://')
        if len(parts) != 2:
            self.log.error(f'sqlite3 connection string should be formed as "sqlite3://<path to database file>" which "{connection_string}" is not')
            exit(1)
        self._connection = sqlite3.connect(parts[1])
        self._cursor = self._connection.cursor()

    def __next__(self) -> Any:
        if self._fetch_result is None:
            raise StopIteration
        try:
            return self._fetch_result.__next__()
        except StopIteration:
            self._fetch_phase = self._fetch_cycle[self._fetch_phase]
            if self._fetch_phase is None:
                raise StopIteration
            elif self._fetch_phase == IPv4Protocol.UDP:
                self._fetch_result = self.run_sql(f'SELECT * from v_udp WHERE timestamp > {self._since}')
            elif self._fetch_phase == IPv4Protocol.ICMP:
                self._fetch_result = self.run_sql(f'SELECT * from v_icmp WHERE timestamp > {self._since}')
            else:
                self._fetch_result = self.run_sql(f'SELECT * from v_any WHERE timestamp > {self._since}')
            return self.__next__()
        
    def fetch(self, since : int) -> Iterator:
        self._since = since
        self._fetch_result = self.run_sql(f'SELECT * FROM v_tcp WHERE timestamp > {self._since}')
        self._fetch_phase = IPv4Protocol.TCP
        return self

    def get_most_recent_timestamp(self) -> int:
        result = self.run_sql('SELECT MAX(timestamp) FROM log_base').fetchone()[0]
        return 0 if result is None else result

    def get_unresolved_geoip(self, nitems : int) -> Iterator:
        result = self.run_sql("""
                                SELECT DISTINCT addr from geoip 
                                WHERE resolved = FALSE
                                LIMIT {:}
                              """.format(nitems))
        return result
                
    def _sanitize(self, s : str) -> str:
        return s.replace('\'', '\'\'')
    
    def start_transaction(self):
        self.run_sql('BEGIN DEFERRED TRANSACTION')

    def commit_transaction(self):
        self.run_sql('COMMIT TRANSACTION')

    def rollback_transaction(self):
        self.run_sql('ROLLBACK TRANSACTION')

    def set_geoip_data(self, addr : str, country : str, c_code : str, city : str, isp : str, org : str, lat : str, lon : str) -> None:
        self.run_sql("""
                        UPDATE geoip 
                        SET resolved = TRUE, country = '{:}', country_code = '{:}', city =  '{:}', isp = '{:}', org = '{:}', lat = {:}, lon = {:}
                        WHERE resolved = FALSE AND addr = '{:}'
                     """.format(self._sanitize(country), c_code, self._sanitize(city), self._sanitize(isp), self._sanitize(org), lat, lon, addr))
        
    def do_import(self, records : Iterator):
        src_addr : str = None
        for record in records:
            try:
                self.run_sql('BEGIN DEFERRED TRANSACTION')
                self.run_sql("""
                    INSERT INTO log_base (timestamp, type, channel, severity)
                        VALUES ({:}, {:}, '{:}', '{:}')
                """.format(
                    int(record.timestamp.replace(tzinfo=timezone.utc).timestamp()),
                    record.type.value,
                    record.channel,
                    record.severity
                ))
                last_id = self._cursor.lastrowid

                if record.type == RecordType.GENERIC:
                    self.run_sql("""
                        INSERT INTO log_messages(log_id, message)
                        VALUES ({:}, '{:}')
                    """.format(last_id, self._sanitize(record.message)))
                    
                elif record.type == RecordType.NETWORK:

                    self.run_sql("""
                        INSERT INTO log_ip(log_id, conn_state, protocol, in_itf)
                        VALUES ({:}, '{:}', {:}, '{:}')
                    """.format(last_id, record.connection_state.value, record.protocol.value, record.in_itf))

                    if record.protocol == IPv4Protocol.TCP:
                        src_addr = record.addresses.src_address                        
                        self.run_sql("""
                            INSERT INTO log_tcp(log_id, tcp_state, src_addr, src_port, dst_addr, dst_port)
                                VALUES ({:}, '{:}', '{:}', {:}, '{:}', {:})
                        """.format(
                            last_id,
                            record.tcp_state,
                            record.addresses.src_address,
                            record.addresses.src_port,
                            record.addresses.dst_address,
                            record.addresses.dst_port
                        ))

                    elif record.protocol == IPv4Protocol.UDP:
                        src_addr = record.addresses.src_address
                        self.run_sql("""
                            INSERT INTO log_udp(log_id, src_addr, src_port, dst_addr, dst_port)
                                VALUES ({:}, '{:}', {:}, '{:}', {:})
                        """.format(
                            last_id,
                            record.addresses.src_address,
                            record.addresses.src_port,
                            record.addresses.dst_address,
                            record.addresses.dst_port
                        ))

                    elif record.protocol == IPv4Protocol.ICMP:
                        src_addr = record.source
                        self.run_sql("""
                            INSERT INTO log_icmp(log_id, type, code, src_addr, dst_addr)
                                VALUES ({:}, {:}, {:}, '{:}', '{:}')
                        """.format(
                            last_id,
                            record.icmp_type,
                            record.icmp_code,
                            record.source,
                            record.destination
                        ))

                    else:
                        src_addr = record.source
                        self.run_sql("""
                            INSERT INTO log_any(log_id, src_addr, dst_addr)
                                VALUES ({:}, '{:}', '{:}')
                        """.format(
                            last_id,
                            record.source,
                            record.destination
                        ))

                    # try to insert into geoip database if not there yet
                    if not str(src_addr).startswith('192.168.'):
                        self.run_sql("""
                            INSERT INTO geoip (log_id, addr) VALUES({:}, '{:}')
                        """.format(last_id, src_addr))
                        
                self.run_sql('COMMIT TRANSACTION')

            except Exception as ex:
                self.log.warning('received exception, will roll back transaction {:}'.format(ex))
                self.run_sql('ROLLBACK TRANSACTION')


    def run_sql(self, sql: str, cursor : sqlite3.Cursor = None) -> Any:
        cursor = self._cursor if cursor is None else cursor

        self.log.debug(f'SQL: {sql}')
        return cursor.execute(sql)

    def create_schema(self):
        self.log.debug("Creating database schema")
        self.run_sql("""
                        CREATE TABLE IF NOT EXISTS log_base (
                            id INTEGER PRIMARY KEY ASC,
                            type INTEGER,
                            timestamp INTEGER,
                            channel text,
                            severity text)
                       """)
        self.run_sql("""
                        CREATE TABLE IF NOT EXISTS log_messages (
                            log_id INTEGER PRIMARY KEY,
                            message TEXT,
                            FOREIGN KEY(log_id) REFERENCES log_base (id))
                        WITHOUT ROWID
                       """)
        self.run_sql("""
                        CREATE TABLE IF NOT EXISTS log_ip (
                            log_id INTEGER PRIMARY KEY,
                            conn_state text,
                            protocol integer,
                            in_itf text,
                            FOREIGN KEY(log_id) REFERENCES log_base (id)
                      )
                      """)
        self.run_sql("""
                        CREATE TABLE IF NOT EXISTS log_tcp (
                            log_id INTEGER PRIMARY KEY,
                            tcp_state text,
                            src_addr text,
                            src_port integer,
                            dst_addr text,
                            dst_port integer,
                            FOREIGN KEY(log_id) REFERENCES log_base (id)
                      )
                      """)
        self.run_sql("""
                        CREATE TABLE IF NOT EXISTS log_udp (
                            log_id INTEGER PRIMARY KEY,
                            src_addr text,
                            src_port integer,
                            dst_addr text,
                            dst_port integer,
                            FOREIGN KEY(log_id) REFERENCES log_base (id)
                      )
                      """)
        self.run_sql("""
                        CREATE TABLE IF NOT EXISTS log_icmp (
                            log_id INTEGER PRIMARY KEY,
                            type integer,
                            code integer,
                            src_addr text,
                            dst_addr text,
                            FOREIGN KEY(log_id) REFERENCES log_base (id)
                      )
                      """)
        self.run_sql("""
                        CREATE TABLE IF NOT EXISTS log_any (
                            log_id INTEGER PRIMARY KEY,
                            src_addr text,
                            dst_addr text,
                            FOREIGN KEY(log_id) REFERENCES log_base (id)
                      )
                      """)
        self.run_sql("""
                        CREATE TABLE IF NOT EXISTS geoip(
                            log_id INTEGER PRIMARY KEY,
                            addr TEXT,
                            resolved BOOLEAN DEFAULT FALSE,
                            country TEXT,
                            country_code TEXT,
                            city TEXT,
                            isp TEXT,
                            org TEXT,
                            lat DECIMAL(10,4),
                            lon DECIMAL(10,4),
                            FOREIGN KEY(log_id) REFERENCES log_base (id)
                      )
                      """)
        self.run_sql("""
                        CREATE VIEW IF NOT EXISTS v_tcp AS
                            SELECT b.*, ip.protocol, ip.conn_state, ip.in_itf, 
                                   tcp.tcp_state, tcp.src_addr, tcp.src_port,
                                   tcp.dst_addr, tcp.dst_port 
                                FROM log_base b
                            FULL OUTER JOIN log_ip ip ON b.id = ip.log_id
                            FULL OUTER JOIN log_tcp tcp ON b.id = tcp.log_id
                            WHERE ip.protocol = 6
                      """)
        self.run_sql("""
                        CREATE VIEW IF NOT EXISTS v_udp AS
                            SELECT b.*, ip.protocol, ip.conn_state, ip.in_itf, 
                                   udp.src_addr, udp.src_port, udp.dst_addr, 
                                   udp.dst_port 
                                FROM log_base b
                            FULL OUTER JOIN log_ip ip ON b.id = ip.log_id
                            FULL OUTER JOIN log_udp udp ON b.id = udp.log_id
                            WHERE ip.protocol = 17
                      """)
        self.run_sql("""
                        CREATE VIEW IF NOT EXISTS v_icmp AS
                            SELECT b.*, ip.protocol, ip.conn_state, ip.in_itf,
                                   icmp.type as icmp_type, icmp.code as icmp_code, 
                                   icmp.src_addr, icmp.dst_addr
                                FROM log_base b
                            FULL OUTER JOIN log_ip ip ON b.id = ip.log_id
                            FULL OUTER JOIN log_icmp icmp ON b.id = icmp.log_id
                            WHERE ip.protocol = 1
                      """)    
        self.run_sql("""
                        CREATE VIEW IF NOT EXISTS v_any AS
                            SELECT b.*, ip.protocol, ip.conn_state, ip.in_itf, 
                                   log_any.src_addr, log_any.dst_addr 
                                FROM log_base b
                            FULL OUTER JOIN log_ip ip ON b.id = ip.log_id
                            FULL OUTER JOIN log_any ON b.id = log_any.log_id
                            WHERE ip.protocol NOT IN (1, 6, 17)
                      """)
        self.run_sql("""
                        CREATE VIEW IF NOT EXISTS v_other AS
                            SELECT b.*, m.message FROM log_base b
                            FULL OUTER JOIN log_messages m ON b.id = m.log_id
                            WHERE b.type = 1
                      """)
        self.run_sql("""
                        CREATE VIEW IF NOT EXISTS v_firewall AS
                            SELECT tcp.id, tcp.timestamp, tcp.severity, tcp.protocol, tcp.conn_state, 
                                   tcp.in_itf, tcp.src_addr, tcp.dst_addr from v_tcp tcp
                        UNION
                            SELECT udp.id, udp.timestamp, udp.severity, udp.protocol, udp.conn_state,
                                   udp.in_itf, udp.src_addr, udp.dst_addr from v_udp udp
                        UNION
                            SELECT icmp.id, icmp.timestamp, icmp.severity, icmp.protocol, icmp.conn_state,
                                   icmp.in_itf, icmp.src_addr, icmp.dst_addr from v_icmp icmp
                        UNION
                            SELECT xany.id, xany.timestamp, xany.severity, xany.protocol, xany.conn_state,
                                   xany.in_itf, xany.src_addr, xany.dst_addr from v_any xany
                      """)
        self.run_sql("""
                        CREATE VIEW IF NOT EXISTS v_tcp_udp AS
                            SELECT tcp.id, tcp.timestamp, tcp.severity, tcp.protocol, tcp.conn_state, 
                                   tcp.in_itf, tcp.src_addr, tcp.src_port, tcp.dst_addr, tcp.dst_port from v_tcp tcp
                        UNION
                            SELECT udp.id, udp.timestamp, udp.severity, udp.protocol, udp.conn_state,
                                   udp.in_itf, udp.src_addr, udp.src_port, udp.dst_addr, udp.dst_port from v_udp udp
                      """)
        self.run_sql("""
                        CREATE VIEW IF NOT EXISTS v_tcp_udp_geo AS
                            SELECT fw.*, geo.country, geo.city, geo.isp, geo.org, geo.lat, geo.lon 
                                FROM v_tcp_udp fw
                            FULL OUTER JOIN geoip geo ON fw.id = geo.log_id
                     """)
        self.run_sql("""
                        CREATE VIEW IF NOT EXISTS v_firewall_geo AS
                            SELECT fw.*, geo.country, geo.city, geo.isp, geo.org, geo.lat, geo.lon 
                                FROM v_firewall fw
                            FULL OUTER JOIN geoip geo ON fw.id = geo.log_id
                     """)

