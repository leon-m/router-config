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
/ip firewall nat    remove       numbers=[find where comment~"$ConfigVerCur"]
/ip firewall raw    remove       numbers=[find where comment~"$ConfigVerCur"]
/ip firewall filter remove       numbers=[find where comment~"$ConfigVerCur"]
/ip firewall address-list remove numbers=[find where comment~"$ConfigVerCur"]
/ip firewall address-list remove numbers=[find where list=blacklist]

:put "    Setting up new address lists"
# -- Intranet
/ip firewall address-list add list=intranet address=$RedZonePool   comment="$ConfigVerNew"
/ip firewall address-list add list=intranet address=$BlueZonePool  comment="$ConfigVerNew"
/ip firewall address-list add list=intranet address=$GreenZonePool comment="$ConfigVerNew"
# -- Maintenance, port 1
/ip firewall address-list add list=support address=192.168.77.2-192.168.77.255 comment="$ConfigVerNew"
/ip firewall address-list add list=support address=$RedZonePool   comment="$ConfigVerNew"
/ip firewall address-list add list=support address=$BlueZonePool  comment="$ConfigVerNew"
/ip firewall address-list add list=support address=$GreenZonePool comment="$ConfigVerNew"

# --- IP Blacklist
/ip firewall address-list add list=blacklist comment="$ConfigVerNew"

# -- Red Zone services
/ip firewall address-list add list=red-services address="$RedZoneNetwork.99" comment="$ConfigVerNew"
/ip firewall address-list add list=red-services address="$RedZoneNetwork.111" comment="$ConfigVerNew"

# -- Digiverse external addresses
/ip firewall address-list add list=digiverse address=77.234.149.122-77.234.149.126 comment="$ConfigVerNew"

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

:put "    Setting port forwarding"
/ip firewall nat add chain=dstnat action=dst-nat to-addresses=192.168.3.76 to-ports=3389 protocol=tcp src-address-list=digiverse dst-port=3389 comment="$ConfigVerNew :allow remote desktop from Digiverse"
/ip firewall nat add chain=dstnat action=dst-nat to-addresses=192.168.3.76 to-ports=3389 protocol=udp src-address-list=digiverse dst-port=3389 comment="$ConfigVerNew :allow remote desktop from Digiverse"

:put "    Restoring NAT service on internet interface"
/ip firewall nat add chain=srcnat out-interface=telekom ipsec-policy=out,none action=masquerade comment="$ConfigVerNew"

:put "    Setting up new filters"
# =============================================================================
# =============================================================================
# ===
# === IPv4 Firewal
# ===
# =============================================================================
# =============================================================================

# --- input chain. protection for router itself
#  Input chain filters processed in the following order
#   1. pass all ICMPs through a separate chain
#   2. accept all establsihed connections
#   3. accept everything arriving on the magenta (admin) interface (see barebone.rsc for where the "magenta" is mapped to)
#   4. accept SSH from anywhere [make sure, though, that only authorized kays may acces it, no username/password access]
#   5. accept DNS queries from intranet
#   6. drop everythign else
/ip firewall raw add chain=prerouting action=drop src-address-list=blacklist comment="$ConfigVerNew :fastrack drop from blacklisted IPs even before routing"
/ip firewall filter add chain=input protocol=icmp action=jump jump-target=chain-icmp comment="$ConfigVerNew :process all ICMPs in a separate chain"
/ip firewall filter add chain=input action=accept connection-state=established,related,untracked comment="$ConfigVerNew :accept all established sessions" 
/ip firewall filter add chain=input action=accept in-interface=magenta comment="$ConfigVerNew :accept all trafic from magenta (admin) interface"
/ip firewall filter add chain=input action=accept dst-port=22 src-address-list=intranet protocol=tcp comment="$ConfigVerNew :accept ssh from intranet"
/ip firewall filter add chain=input action=accept dst-port=22 src-address-list=digiverse protocol=tcp comment="$ConfigVerNew :accept ssh from Digiverse"
/ip firewall filter add chain=input action=accept dst-port=53 protocol=tcp in-interface-list=intranet comment="$ConfigVerNew :accept DNS queries from intranet; tcp"
/ip firewall filter add chain=input action=accept dst-port=53 protocol=udp in-interface-list=intranet comment="$ConfigVerNew :accept DNS queries from intranet; udp"
/ip firewall filter add chain=input action=add-src-to-address-list address-list=blacklist address-list-timeout=24h in-interface=telekom comment="$ConfigVerNew :log and blacklist dropped connect attemts" log=yes log-prefix="#BLACKLISTED: "
/ip firewall filter add chain=input action=drop comment="$ConfigVerNew :drop all not explicitly accepted packets" 

# --- protection for LAN, forward chain
# Forward chain filters processed in the following order
# 1. accept/fastrack everything for known connections
# 2. drop invalid connections
# 3. drop anything targeted to private numbers and going from intranet to internet
# 7. process icmp packets via ICMP chain
# 4. drop everything coming from internet but not going through NAT
# 5. drop evertything arriving from internet with source address being one of private numbers
# 6. for each zone drop packets arriving from intranet zones but not having zone source address
# 8. accept the rest of the lot
/ip firewall filter add chain=forward action=fasttrack-connection connection-state=established,related comment="$ConfigVerNew"
/ip firewall filter add chain=forward action=accept connection-state=established,related,untracked comment="$ConfigVerNew" 
/ip firewall filter add chain=forward action=drop connection-state=invalid log=yes log-prefix="!invalid:" comment="$ConfigVerNew" 

# Interzone traffic as follows:
#   - red zone can go to any other zone, as is default
#   - blue zone can go to green zone (default) and selected services in red zone
#   - green zone can go to no other zone
/ip firewall filter add chain=forward action=jump jump-target=chain-red in-interface-list=guest out-interface=zone-red comment="$ConfigVerNew :controll traffic between zones in a separate chain"
/ip firewall filter add chain=forward action=drop in-interface=zone-green out-interface=zone-blue comment="$ConfigVerNew :protect blue zone from green zone"

# ICMP processing goes to separate list
/ip firewall filter add chain=forward action=jump jump-target=chain-icmp protocol=icmp in-interface-list=intranet  comment="$ConfigVerNew :process all ICMPs in a separate chain"

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
/ip firewall filter add chain=forward action=accept comment="$ConfigVerNew"

# -- ICMP processing chain
# see https://www.iana.org/assignments/icmp-parameters/icmp-parameters.xhtml for ICMP types and codes
# Acept eveything if originates from Intranet, block extended echo, redirect and traceroute requests from elsewhere
/ip firewall filter add chain=chain-icmp action=accept in-interface-list=intranet comment="$ConfigVerNew :accept everything from Intranet regardless where it goes" 
/ip firewall filter add chain=chain-icmp protocol=icmp action=drop icmp-options=42:0 in-interface-list=internet comment="$ConfigVerNew :block extended echo requests"
/ip firewall filter add chain=chain-icmp protocol=icmp action=drop icmp-options=5:0-3 in-interface-list=internet comment="$ConfigVerNew :block redirect requests"
/ip firewall filter add chain=chain-icmp protocol=icmp action=drop icmp-options=30:0 in-interface-list=internet comment="$ConfigVerNew :block traceroute requests"
# TODO: consider logging them
/ip firewall filter add chain=chain-icmp action=accept in-interface-list=internet comment="$ConfigVerNew :accept other ICMP requests"

# Interzone traffic
/ip firewall filter add chain=chain-red action=accept in-interface=zone-blue dst-address-list=red-services comment="$ConfigVerNew :accept access to red zone services from blue zone"
/ip firewall filter add chain=chain-red action=drop comment="$ConfigVerNew: but drop other requests from blue zone and all requests from green zone"

# ##################
# TODO: For now we'll disable IPv6 settings
# ##################

:put "    Removing temporary defensive filters"
/ip firewall filter remove numbers=[find where comment="temporary fence"]