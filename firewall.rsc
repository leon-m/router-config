global RedZoneNetwork
global RedZoneIp
global RedZonePool
global GreenZoneNetwork
global GreenZoneIp
global GreenZonePool
global BlueZoneNetwork
global BlueZoneIp
global BlueZonePool

global ConfigVerCur
global ConfigVerNew

:put "  Firewall configuration"

:put "    Setting up temporary defensive filters"
/ip   firewall filter add chain=input action=accept dst-port=22 protocol=tcp      comment="temporary fence"
/ip   firewall filter add chain=input action=drop   in-interface-list=internet comment="temporary fence"
/ipv6 firewall filter add chain=input action=drop   in-interface-list=internet comment="temporary fence"

:put "    Temporarily disabling NAT and removing old firewall filters"
/ip firewall nat    remove       numbers=[find where comment="$ConfigVerCur"]
/ip firewall filter remove       numbers=[find where comment="$ConfigVerCur"]
/ip firewall address-list remove numbers=[find where comment="$ConfigVerCur"]

:put "    Setting up new ddress lists"
# -- Intranet
/ip firewall address-list add list=intranet address=$RedZonePool   comment="$ConfigVerNew"
/ip firewall address-list add list=intranet address=$BlueZonePool  comment="$ConfigVerNew"
/ip firewall address-list add list=intranet address=$GreenZonePool comment="$ConfigVerNew"
# -- Maintenance, port 1
/ip firewall address-list add list=support address=192.168.77.2-192.168.77.255 comment="$ConfigVerNew"
/ip firewall address-list add list=support address=$RedZonePool   comment="$ConfigVerNew"
/ip firewall address-list add list=support address=$BlueZonePool  comment="$ConfigVerNew"
/ip firewall address-list add list=support address=$GreenZonePool comment="$ConfigVerNew"

# -- IPv4 network numbers we don't want to route - mostly private numbers
# -- See https://en.wikipedia.org/wiki/Reserved_IP_addresses for summary
# RFC3330 - self identification, local (this) network
/ip firewall address-list add list=ipv4_private address=0.0.0.0/8       comment="$ConfigVerNew"
# RFC1918 - private numbers, class A
/ip firewall address-list add list=ipv4_private address=10.0.0.0/8      comment="$ConfigVerNew"
# RFC1918 - private numbers, class B
/ip firewall address-list add list=ipv4_private address=172.16.0.0/12   comment="$ConfigVerNew"
# RFC1918 - private numbers, class C
/ip firewall address-list add list=ipv4_private address=192.168.0.0/16  comment="$ConfigVerNew"
# RFC3330 - Link local
/ip firewall address-list add list=ipv4_private address=169.254.0.0/16  comment="$ConfigVerNew"
# Reserved - IANA TestNet1, TestNet2, TestNet3
/ip firewall address-list add list=ipv4_private address=192.0.2.0/24    comment="$ConfigVerNew"
/ip firewall address-list add list=ipv4_private address=198.51.100.0/24 comment="$ConfigVerNew"
/ip firewall address-list add list=ipv4_private address=203.0.113.0/24  comment="$ConfigVerNew"
# RFC3330 - Loopback
/ip firewall address-list add list=ipv4_private address=127.0.0.0/8     comment="$ConfigVerNew"
# NIDB (benchmark) testing
/ip firewall address-list add list=ipv4_private address=198.18.0.0/15   comment="$ConfigVerNew"
# RFC3068 -  6to4 relay Anycast
/ip firewall address-list add list=ipv4_private address=192.88.99.0/24  comment="$ConfigVerNew"
# IETF Protocol Assignment
/ip firewall address-list add list=ipv4_private address=192.0.0.0/24    comment="$ConfigVerNew"
# Shared address space for ISP/subscriber communication
/ip firewall address-list add list=ipv4_private address=100.64.0.0/10   comment="$ConfigVerNew"
# Multicast Class D, IANA
/ip firewall address-list add list=ipv4_private address=224.0.0.0/4 disabled=no  comment="$ConfigVerNew"
# MCAST-TEST-NET enable if removing general mcast above (224.0.0.0/4) from the list
/ip firewall address-list add list=ipv4_private address=233.252.0.0/24 disabled=yes comment="$ConfigVerNew"
# Reserved for future use
/ip firewall address-list add list=ipv4_private address=240.0.0.0/4 comment="$ConfigVerNew"
# Do not forward broadcast
/ip firewall address-list add list=ipv4_private address=255.255.255.255/32 comment="$ConfigVerNew"


:put "    Restoring NAT service on internet interface"
/ip firewall nat add chain=srcnat out-interface-list=internet ipsec-policy=out,none action=masquerade comment="$ConfigVerNew"

:put "    Setting up new filters"
# =============================================================================
# =============================================================================
# ===
# === IPv4 Firewal
# ===
# =============================================================================
# =============================================================================

# --- protection for router itself, input chain
#  Input chain filters processed in the following order
#   1. accept everything for known connections
#   2. accept everything arriving on the admin interface (see barebone.rsc for where the "admin" is mapped to)
#   3. accept SSH from anywhere [make sure, though, that only authorized kays may acces it, no username/password access]
#   4. accept DNS queries from intranet
#   5. process ICMPs via ICMP input chain
#   6. drop the rest
/ip firewall filter add chain=input action=accept connection-state=established,related,untracked comment="$ConfigVerNew" 
/ip firewall filter add chain=input action=accept in-interface="admin" comment="$ConfigVerNew"
/ip firewall filter add chain=input action=accept dst-port=22 protocol=tcp comment="$ConfigVerNew"
/ip firewall filter add chain=input action=accept dst-port=53 protocol=tcp in-interface-list=intranet comment="$ConfigVerNew"
/ip firewall filter add chain=input action=accept dst-port=53 protocol=udp in-interface-list=intranet comment="$ConfigVerNew"
/ip firewall filter add chain=input action=jump jump-target=in-icmp protocol=icmp comment="$ConfigVerNew"
/ip firewall filter add chain=input action=drop comment="$ConfigVerNew" 

# --- protection for LAN, forward chain
# Forward chain filters processed in the following order
# 1. accept/fastrack everything for known connections
# 2. drop invalid connections
# 3. drop anything targeted to private numbers and going from intranet to internet
# 4. drop everything coming from internet but not going through NAT
# 5. drop evertything arriving from internet with source address being one of private numbers
# 6. for each zone drop packets arriving from intranet zones but not having zone source address
# 7. process icmp packets via ICMP chain
# 8. accept the rest of the lot
/ip firewall filter add chain=forward action=fasttrack-connection connection-state=established,related comment="$ConfigVerNew"
/ip firewall filter add chain=forward action=accept connection-state=established,related,untracked comment="$ConfigVerNew" 
/ip firewall filter add chain=forward action=drop connection-state=invalid log=yes log-prefix="!invalid:" comment="$ConfigVerNew" 
# Drop connection attempts to non-public addresses
/ip firewall filter add chain=forward action=drop dst-address-list=ipv4_private in-interface-list=intranet out-interface-list=internet log=yes log-prefix="!private number:" comment="$ConfigVerNew" 
# Drop incoming packets that were not NAT'ed
/ip firewall filter add chain=foward action=drop connection-nat-state=!dstnat connection-state=new in-interface-list=internet log=yes log-prefix="!nat:" comment="$ConfigVerNew" 
# Drop incoming packets from internet that are not from public addresses
/ip firewall filter add chain=forward action=drop in-interface-list=internet src-address-list=ipv4_private log=yes log-prefix="!private number:" comment="$ConfigVerNew" 
# And drop packets from LAN that do not have LAN addresses - do this for each zone separately
/ip firewall filter add chain=forward action=drop in-interface=zone-red   src-address="!$RedZoneNetwork.0/24"   log=yes log-prefix="!red address:" comment="$ConfigVerNew"
/ip firewall filter add chain=forward action=drop in-interface=zone-blue  src-address="!$BlueZoneNetwork.0/24"  log=yes log-prefix="!blue address:" comment="$ConfigVerNew"
/ip firewall filter add chain=forward action=drop in-interface=zone-green src-address="!$GreenZoneNetwork.0/24" log=yes log-prefix="!green address:" comment="$ConfigVerNew"
/ip firewall filter add chain=forward action=jump jump-target=in-icmp protocol=icmp comment="$ConfigVerNew"
/ip firewall filter add chain=forward action=accept comment="$ConfigVerNew"

# -- ICMP chain for input chain
# see https://www.iana.org/assignments/icmp-parameters/icmp-parameters.xhtml for ICMP types and codes

# acecpt everything from LAN
/ip firewall filter add chain=in-icmp action=accept protocol=icmp in-interface-list=intranet comment="$ConfigVerNew" 
# as for the sharks-be-there Internet, let's start by blocking redirect and echo requests only.  
# echo request
/ip firewall filter add chain=in-icmp action=drop protocol=icmp icmp-options=8:0 in-interface-list=internet comment="$ConfigVerNew"
# extended echo request
/ip firewall filter add chain=in-icmp action=drop protocol=icmp icmp-options=42:0 in-interface-list=internet comment="$ConfigVerNew"
# type 5 - redirect
/ip firewall filter add chain=in-icmp action=drop protocol=icmp icmp-options=5:0-3 in-interface-list=internet comment="$ConfigVerNew"
# type 30 - traceroute, deprecated, drop nonetheless
/ip firewall filter add chain=in-icmp action=drop protocol=icmp icmp-options=30:0 in-interface-list=internet comment="$ConfigVerNew"
# as for the rest - accept them for now but observe log. They can be used for DOS type of attacks, eg. type 3 to force router to keep
# reconecting. Perhaps complement this using techniques for [D]DoS prevention
/ip firewall filter add chain=in-icmp action=accept protocol=icmp in-interface-list=internet log=yes log-prefix="!icmp" comment="$ConfigVerNew"

# TODO: For now we'll disable IPv6 settings
:put "    Removing temporary defensive filters"
/ip firewall filter remove numbers=[find where comment="temporary fence"]