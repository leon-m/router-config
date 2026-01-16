
from typing import Any, Iterator
from datetime import timezone
import psycopg

from lib.logging import get_logger
from lib.log_model import RecordType
from lib.ipv4 import IPv4Protocol
from lib.db_adapter import DbAdapter, Username

class PostgreSqlAdapter(DbAdapter):
    version : int = 1
    schema : str = f'v{version}'

    def __init__(self, connection_string : str) -> None:
        self.log = get_logger(__name__)
        self._fetch_phase = None
        self._fetch_result = None
        self._fetch_cycle = { IPv4Protocol.TCP : IPv4Protocol.UDP, IPv4Protocol.UDP : IPv4Protocol.ICMP, IPv4Protocol.ICMP : IPv4Protocol.RESERVED, IPv4Protocol.RESERVED : None }
        self._since = 0

        self.connection = psycopg.connect(conninfo=connection_string, autocommit=True)
        self.cursor = self.connection.cursor()

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
                self._fetch_result = self.run_sql(f'SELECT * from v1.v_udp WHERE timestamp > {self._since}')
            elif self._fetch_phase == IPv4Protocol.ICMP:
                self._fetch_result = self.run_sql(f'SELECT * from v1.v_icmp WHERE timestamp > {self._since}')
            else:
                self._fetch_result = self.run_sql(f'SELECT * from v1.v_any WHERE timestamp > {self._since}')
            return self.__next__()
        
    def fetch(self, since : int) -> Iterator:
        self._since = since
        self._fetch_result = self.run_sql(f'SELECT * FROM v1.v_tcp WHERE timestamp > {self._since}')
        self._fetch_phase = IPv4Protocol.TCP
        return self

    def get_most_recent_timestamp(self) -> int:
        result = self.run_sql('SELECT MAX(timestamp) FROM v1.log_base').fetchone()[0]
        return 0 if result is None else result

    def get_unresolved_geoip(self, nitems : int) -> Iterator:
        result = self.run_sql("""
                                SELECT addr from {:}.geoip 
                                WHERE resolved = FALSE AND addr NOT LIKE '192.168.%'
                                FETCH FIRST {:} ROWS ONLY
                              """.format(self.schema, nitems))
        return result
    
    def _sanitize(self, s : str) -> str:
        return s.replace('\'', '\'\'')
    
    def set_geoip_data(self, addr : str, country : str, c_code : str, city : str, isp : str, org : str, lat : str, lon : str) -> None:
        self.run_sql("""
                        UPDATE {:}.geoip 
                        SET resolved = TRUE,
                            country = '{:}', country_code = '{:}', city =  '{:}',
                            isp = '{:}', org = '{:}', lat = {:}, lon = {:}
                        WHERE addr = '{:}'
                     """.format(self.schema, self._sanitize(country), c_code, self._sanitize(city), self._sanitize(isp), self._sanitize(org), lat, lon, addr))
        
    def do_import(self, records : Iterator):
        src_addr : str = None
        for record in records:
            if record.type == RecordType.GENERIC:
                self.log.debug(f'will insert log record: {record}')
                self.run_sql("""
                    with new_record as (
                        insert into {:}.log_base(timestamp, type, channel, severity)
                                    values ({:}, {:}, '{:}', '{:}')
                        returning id
                    )
                    insert into {:}.log_messages(log_id, message)
                        select id, '{:}' from new_record
                """.format(
                    self.schema,
                    int(record.timestamp.replace(tzinfo=timezone.utc).timestamp()),
                    record.type.value,
                    record.channel,
                    record.severity,
                    self.schema,
                    record.message
                ))
            elif record.type == RecordType.NETWORK:
                if record.protocol == IPv4Protocol.TCP:
                    src_addr = record.addresses.src_address
                    self.run_sql("""
                        WITH new_record AS (
                            INSERT INTO {:}.log_base(timestamp, type, channel, severity)
                                  VALUES({:}, {:}, '{:}', '{:}')
                            RETURNING id
                        ),
                        new_ip AS (INSERT INTO {:}.log_ip(log_id, conn_state, protocol, in_itf)
                            SELECT id, '{:}', {:}, '{:}' FROM new_record
                            RETURNING log_id
                        )
                        INSERT INTO {:}.log_tcp(log_id, tcp_state, src_addr, src_port, dst_addr, dst_port)
                            SELECT log_id, '{:}', '{:}', {:}, '{:}', {:} FROM new_ip
                    """.format(
                        self.schema,
                        int(record.timestamp.replace(tzinfo=timezone.utc).timestamp()),
                        record.type.value,
                        record.channel,
                        record.severity,
                        self.schema,
                        record.connection_state.value,
                        record.protocol.value,
                        record.in_itf,
                        self.schema,
                        record.tcp_state,
                        record.addresses.src_address,
                        record.addresses.src_port,
                        record.addresses.dst_address,
                        record.addresses.dst_port
                    ))
                elif record.protocol == IPv4Protocol.UDP:
                    src_addr = record.addresses.src_address
                    self.run_sql("""
                        WITH new_record AS (
                            INSERT INTO {:}.log_base(timestamp, type, channel, severity)
                                  VALUES({:}, {:}, '{:}', '{:}')
                            RETURNING id
                        ),
                        new_ip AS (INSERT INTO {:}.log_ip(log_id, conn_state, protocol, in_itf)
                            SELECT id, '{:}', {:}, '{:}' FROM new_record
                            RETURNING log_id
                        )
                        INSERT INTO {:}.log_udp(log_id, src_addr, src_port, dst_addr, dst_port)
                            SELECT log_id, '{:}', {:}, '{:}', {:} FROM new_ip
                    """.format(
                        self.schema,
                        int(record.timestamp.replace(tzinfo=timezone.utc).timestamp()),
                        record.type.value,
                        record.channel,
                        record.severity,
                        self.schema,
                        record.connection_state.value,
                        record.protocol.value,
                        record.in_itf,
                        self.schema,
                        record.addresses.src_address,
                        record.addresses.src_port,
                        record.addresses.dst_address,
                        record.addresses.dst_port
                    ))
                elif record.protocol == IPv4Protocol.ICMP:
                    src_addr = record.source
                    self.run_sql("""
                        WITH new_record AS (
                            INSERT INTO {:}.log_base(timestamp, type, channel, severity)
                                  VALUES({:}, {:}, '{:}', '{:}')
                            RETURNING id
                        ),
                        new_ip AS (INSERT INTO {:}.log_ip(log_id, conn_state, protocol, in_itf)
                            SELECT id, '{:}', {:}, '{:}' FROM new_record
                            RETURNING log_id
                        )
                        INSERT INTO {:}.log_icmp(log_id, type, code, src_addr, dst_addr)
                            SELECT log_id, {:}, {:}, '{:}', '{:}' FROM new_ip
                    """.format(
                        self.schema,
                        int(record.timestamp.replace(tzinfo=timezone.utc).timestamp()),
                        record.type.value,
                        record.channel,
                        record.severity,
                        self.schema,
                        record.connection_state.value,
                        record.protocol.value,
                        record.in_itf,
                        self.schema,
                        record.icmp_type,
                        record.icmp_code,
                        record.source,
                        record.destination
                    ))
                else:
                    src_addr = record.source
                    self.run_sql("""
                        WITH new_record AS (
                            INSERT INTO {:}.log_base(timestamp, type, channel, severity)
                                  VALUES({:}, {:}, '{:}', '{:}')
                            RETURNING id
                        ),
                        new_ip AS (INSERT INTO {:}.log_ip(log_id, conn_state, protocol, in_itf)
                            SELECT id, '{:}', {:}, '{:}' FROM new_record
                            RETURNING log_id
                        )
                        INSERT INTO {:}.log_any(log_id, src_addr, dst_addr)
                            SELECT log_id, '{:}', '{:}' FROM new_ip
                    """.format(
                        self.schema,
                        int(record.timestamp.replace(tzinfo=timezone.utc).timestamp()),
                        record.type.value,
                        record.channel,
                        record.severity,
                        self.schema,
                        record.connection_state.value,
                        record.protocol.value,
                        record.in_itf,
                        self.schema,
                        record.source,
                        record.destination
                    ))
                
                # try to insert into geoip database if not there yet
                if not str(src_addr).startswith('192.168.'):
                    self.run_sql("""
                                    INSERT INTO {:}.geoip (addr) VALUES('{:}')
                                        ON CONFLICT (addr) DO NOTHING
                                """.format(self.schema, src_addr))

    def run_sql(self, sql: str, cursor : psycopg.Cursor = None) -> Any:
        cursor = self.cursor if cursor is None else cursor

        self.log.debug(f'SQL: {sql}')
        return cursor.execute(sql)

    def create_schema(self):
        self.log.debug("Creating database schema")
        self.run_sql(f'CREATE SCHEMA {self.schema}')
        self.run_sql("""
                        CREATE TABLE {:}.log_base (
                            id bigserial PRIMARY KEY,
                            type smallint,
                            timestamp bigint,
                            channel text,
                            severity text)
                       """.format(self.schema))
        self.run_sql("""
                        CREATE TABLE {:}.log_messages (
                            log_id bigint REFERENCES {:}.log_base (id),
                            message text)
                       """.format(self.schema, self.schema))
        self.run_sql("""
                        CREATE TABLE {:}.log_ip (
                            log_id bigint REFERENCES {:}.log_base(id),
                            conn_state text,
                            protocol smallint,
                            in_itf text
                      )
                      """.format(self.schema, self.schema))
        self.run_sql("""
                        CREATE TABLE {:}.log_tcp (
                            log_id bigint REFERENCES {:}.log_base(id),
                            tcp_state text,
                            src_addr text,
                            src_port integer,
                            dst_addr text,
                            dst_port integer
                      )
                      """.format(self.schema, self.schema))
        self.run_sql("""
                        CREATE TABLE {:}.log_udp (
                            log_id bigint REFERENCES {:}.log_base(id),
                            src_addr text,
                            src_port integer,
                            dst_addr text,
                            dst_port integer
                      )
                      """.format(self.schema, self.schema))
        self.run_sql("""
                        CREATE TABLE {:}.log_icmp (
                            log_id bigint REFERENCES {:}.log_base(id),
                            type smallint,
                            code smallint,
                            src_addr text,
                            dst_addr text
                      )
                      """.format(self.schema, self.schema))
        self.run_sql("""
                        CREATE TABLE {:}.log_any (
                            log_id bigint REFERENCES {:}.log_base(id),
                            src_addr text,
                            dst_addr text
                      )
                      """.format(self.schema, self.schema))
        self.run_sql("""
                        CREATE TABLE {:}.geoip(
                            addr TEXT PRIMARY KEY,
                            resolved BOOLEAN DEFAULT FALSE,
                            country TEXT,
                            country_code TEXT,
                            city TEXT,
                            isp TEXT,
                            org TEXT,
                            lat DECIMAL(10,4),
                            lon DECIMAL(10,4)
                      )
                      """.format(self.schema))
        self.run_sql("""
                        CREATE VIEW v1.v_tcp AS
                            SELECT b.*, ip.protocol, ip.conn_state, ip.in_itf, 
                                   tcp.tcp_state, tcp.src_addr, tcp.src_port,
                                   tcp.dst_addr, tcp.dst_port 
                                FROM v1.log_base b
                            FULL OUTER JOIN v1.log_ip ip ON b.id = ip.log_id
                            FULL OUTER JOIN v1.log_tcp tcp ON b.id = tcp.log_id
                            WHERE ip.protocol = 6
                      """)
        self.run_sql("""
                        CREATE VIEW v1.v_udp AS
                            SELECT b.*, ip.protocol, ip.conn_state, ip.in_itf, 
                                   udp.src_addr, udp.src_port, udp.dst_addr, 
                                   udp.dst_port 
                                FROM v1.log_base b
                            FULL OUTER JOIN v1.log_ip ip ON b.id = ip.log_id
                            FULL OUTER JOIN v1.log_udp udp ON b.id = udp.log_id
                            WHERE ip.protocol = 17
                      """)
        self.run_sql("""
                        CREATE VIEW v1.v_icmp AS
                            SELECT b.*, ip.protocol, ip.conn_state, ip.in_itf,
                                   icmp.type as icmp_type, icmp.code as icmp_code, 
                                   icmp.src_addr, icmp.dst_addr
                                FROM v1.log_base b
                            FULL OUTER JOIN v1.log_ip ip ON b.id = ip.log_id
                            FULL OUTER JOIN v1.log_icmp icmp ON b.id = icmp.log_id
                            WHERE ip.protocol = 1
                      """)    
        self.run_sql("""
                        CREATE VIEW v1.v_any AS
                            SELECT b.*, ip.protocol, ip.conn_state, ip.in_itf, 
                                   v1.log_any.src_addr, v1.log_any.dst_addr 
                                FROM v1.log_base b
                            FULL OUTER JOIN v1.log_ip ip ON b.id = ip.log_id
                            FULL OUTER JOIN v1.log_any ON b.id = v1.log_any.log_id
                            WHERE ip.protocol NOT IN (1, 6, 17)
                      """)
        self.run_sql("""
                        CREATE VIEW v1.v_other AS
                            SELECT b.*, m.message FROM v1.log_base b
                            FULL OUTER JOIN v1.log_messages m ON b.id = m.log_id
                            WHERE b.type = 1
                      """)
        self.run_sql("""
                        CREATE VIEW v1.v_firewall AS
                            SELECT tcp.id, tcp.timestamp, tcp.severity, tcp.protocol, tcp.conn_state, 
                                   tcp.in_itf, tcp.src_addr, tcp.dst_addr from v1.v_tcp tcp
                        UNION
                            SELECT udp.id, udp.timestamp, udp.severity, udp.protocol, udp.conn_state,
                                   udp.in_itf, udp.src_addr, udp.dst_addr from v1.v_udp udp
                        UNION
                            SELECT icmp.id, icmp.timestamp, icmp.severity, icmp.protocol, icmp.conn_state,
                                   icmp.in_itf, icmp.src_addr, icmp.dst_addr from v1.v_icmp icmp
                        UNION
                            SELECT xany.id, xany.timestamp, xany.severity, xany.protocol, xany.conn_state,
                                   xany.in_itf, xany.src_addr, xany.dst_addr from v1.v_any xany
                      """)
        

    def _init_db(self, cursor: psycopg.Cursor, dbname : str, loguser : Username) -> None:
        self.log.info(f'Database {dbname} to store processed router logs was not found, will create one')
        
        result = cursor.execute(f'SELECT usename FROM pg_catalog.pg_user where usename = \'{loguser.username}\'').fetchone()
        self.log.debug(f'query result: {result}')
        if len(result) < 1:
            self.log.info(f'Database owner {loguser.username} not found, will create new user')
            cursor.execute(f'CREATE USER {loguser.username} WITH ENCRYPTED PASSWORD \'{loguser.password}\'')

        # create new database and make loguser its owner
        self.log.info(f'ceating database "{dbname}"')
        result = cursor.execute(f'CREATE DATABASE {dbname} WITH OWNER={loguser.username}')
        
