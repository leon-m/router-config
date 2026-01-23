CREATE TABLE IF NOT EXISTS log_base (
    id INTEGER PRIMARY KEY ASC,
    type INTEGER,
    timestamp INTEGER,
    channel TEXT,
    severity TEXT);

CREATE TABLE IF NOT EXISTS log_messages (
    log_id INTEGER PRIMARY KEY,
    message TEXT,
    FOREIGN KEY(log_id) REFERENCES log_base (id)
);

CREATE TABLE IF NOT EXISTS log_ip (
    log_id INTEGER PRIMARY KEY,
    conn_state TEXT,
    protocol INTEGER,
    in_itf TEXT,
    blacklisted BOOLEAN,
    src_addr TEXT,
    dst_addr TEXT,
    FOREIGN KEY(log_id) REFERENCES log_base (id)
);

CREATE TABLE IF NOT EXISTS log_tcp (
    log_id INTEGER PRIMARY KEY,
    tcp_state TEXT,
    src_port INTEGER,
    dst_port INTEGER,
    FOREIGN KEY(log_id) REFERENCES log_base (id)
);

CREATE TABLE IF NOT EXISTS log_udp (
    log_id INTEGER PRIMARY KEY,
    src_port INTEGER,
    dst_port INTEGER,
    FOREIGN KEY(log_id) REFERENCES log_base (id)
);

CREATE TABLE IF NOT EXISTS log_icmp (
    log_id INTEGER PRIMARY KEY,
    type INTEGER,
    code INTEGER,
    FOREIGN KEY(log_id) REFERENCES log_base (id)
);

CREATE TABLE IF NOT EXISTS log_any (
    log_id INTEGER PRIMARY KEY,
    FOREIGN KEY(log_id) REFERENCES log_base (id)
);

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
);

CREATE TABLE IF NOT EXISTS blacklist(
    addr TEXT PRIMARY KEY
);

DROP VIEW IF EXISTS v_tcp_udp_geo;
DROP VIEW IF EXISTS v_firewall_geo;
DROP VIEW IF EXISTS v_tcp_udp;
DROP VIEW IF EXISTS v_firewall;
DROP VIEW IF EXISTS v_tcp;
DROP VIEW IF EXISTS v_udp;
DROP VIEW IF EXISTS v_icmp;
DROP VIEW IF EXISTS v_any;
DROP VIEW IF EXISTS v_other;

CREATE VIEW v_tcp AS
    SELECT b.*, ip.protocol, ip.conn_state, ip.in_itf, 
	   tcp.tcp_state, ip.src_addr, tcp.src_port,
	   ip.dst_addr, tcp.dst_port, ip.blacklisted
	FROM log_base b
    FULL OUTER JOIN log_ip ip ON b.id = ip.log_id
    FULL OUTER JOIN log_tcp tcp ON b.id = tcp.log_id
    WHERE ip.protocol = 6;

CREATE VIEW v_udp AS
    SELECT b.*, ip.protocol, ip.conn_state, ip.in_itf, 
	   ip.src_addr, udp.src_port, ip.dst_addr, 
	   udp.dst_port, ip.blacklisted
	FROM log_base b
    FULL OUTER JOIN log_ip ip ON b.id = ip.log_id
    FULL OUTER JOIN log_udp udp ON b.id = udp.log_id
    WHERE ip.protocol = 17;

CREATE VIEW v_icmp AS
    SELECT b.*, ip.protocol, ip.conn_state, ip.in_itf,
	   icmp.type as icmp_type, icmp.code as icmp_code, 
	   ip.src_addr, ip.dst_addr, ip.blacklisted
	FROM log_base b
    FULL OUTER JOIN log_ip ip ON b.id = ip.log_id
    FULL OUTER JOIN log_icmp icmp ON b.id = icmp.log_id
    WHERE ip.protocol = 1;

CREATE VIEW v_any AS
    SELECT b.*, ip.protocol, ip.conn_state, ip.in_itf, 
	   ip.src_addr, ip.dst_addr, ip.blacklisted
	FROM log_base b
    FULL OUTER JOIN log_ip ip ON b.id = ip.log_id
    FULL OUTER JOIN log_any ON b.id = log_any.log_id
    WHERE ip.protocol NOT IN (1, 6, 17);

CREATE VIEW v_other AS
    SELECT b.*, m.message FROM log_base b
    FULL OUTER JOIN log_messages m ON b.id = m.log_id
    WHERE b.type = 1;

CREATE VIEW v_firewall AS
    SELECT tcp.id, tcp.timestamp, tcp.severity, tcp.protocol, tcp.conn_state, 
	   tcp.in_itf, tcp.src_addr, tcp.dst_addr, tcp.blacklisted
    FROM  v_tcp tcp
UNION
    SELECT udp.id, udp.timestamp, udp.severity, udp.protocol, udp.conn_state,
	   udp.in_itf, udp.src_addr, udp.dst_addr, udp.blacklisted
    FROM  v_udp udp
UNION
    SELECT icmp.id, icmp.timestamp, icmp.severity, icmp.protocol, icmp.conn_state,
	   icmp.in_itf, icmp.src_addr, icmp.dst_addr, icmp.blacklisted
    FROM  v_icmp icmp
UNION
    SELECT xany.id, xany.timestamp, xany.severity, xany.protocol, xany.conn_state,
	   xany.in_itf, xany.src_addr, xany.dst_addr, xany.blacklisted
    FROM  v_any xany;

CREATE VIEW v_tcp_udp AS
    SELECT tcp.id, tcp.timestamp, tcp.severity, tcp.protocol, tcp.conn_state, 
	   tcp.in_itf, tcp.src_addr, tcp.src_port, tcp.dst_addr, tcp.dst_port,
           tcp.blacklisted
    FROM  v_tcp tcp
UNION
    SELECT udp.id, udp.timestamp, udp.severity, udp.protocol, udp.conn_state,
	   udp.in_itf, udp.src_addr, udp.src_port, udp.dst_addr, udp.dst_port,
       udp.blacklisted
    FROM  v_udp udp;

CREATE VIEW v_tcp_udp_geo AS
    SELECT fw.*, geo.country, geo.city, geo.isp, geo.org, geo.lat, geo.lon 
        FROM v_tcp_udp fw
    LEFT JOIN geoip geo ON fw.id = geo.log_id 
    WHERE fw.src_addr NOT LIKE '192.168.%' AND geo.resolved = TRUE;

CREATE VIEW v_firewall_geo AS
    SELECT fw.*, geo.country, geo.city, geo.isp, geo.org, geo.lat, geo.lon 
        FROM v_firewall fw
    LEFT JOIN geoip geo ON fw.id = geo.log_id 
    WHERE fw.src_addr NOT LIKE '192.168.%' AND geo.resolved = TRUE;

