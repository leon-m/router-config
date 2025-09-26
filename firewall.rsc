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
global step

:put "Step $step. Firewall configuration"

:put "    Setting up temporary defensive filters"
/ip   firewall filter add chain=input action=drop in-interface-list=internet comment="temporary fence"
/ipv6 firewall filter add chain=input action=drop in-interface-list=internet comment="temporary fence"

:put "    Temporarily disabling NAT and removing old firewall filters"
/ip firewall nat    remove       numbers=[find where comment="$ConfigVerCur"]
/ip firewall filter remove       numbers=[find where comment="$ConfigVerCur"]
/ip firewall address-list remove numbers=[find where comment="$ConfigVerCur"]

:put "    Setting up new ddress lists"
/ip firewall address-list add list=intranet address=$RedZonePool   comment="$ConfigVerNew"
/ip firewall address-list add list=intranet address=$BlueZonePool  comment="$ConfigVerNew"
/ip firewall address-list add list=intranet address=$GreenZonePool comment="$ConfigVerNew"
# RFC6890
/ip firewall add list=ipv4_private address=0.0.0.0/8       comment="$ConfigVerNew"
/ip firewall add list=ipv4_private address=172.16.0.0/12   comment="$ConfigVerNew"
/ip firewall add list=ipv4_private address=192.168.0.0/16  comment="$ConfigVerNew"
/ip firewall add list=ipv4_private address=10.0.0.0/8      comment="$ConfigVerNew"
/ip firewall add list=ipv4_private address=169.254.0.0/16  comment="$ConfigVerNew"
/ip firewall add list=ipv4_private address=127.0.0.0/8     comment="$ConfigVerNew"
/ip firewall add list=ipv4_private address=198.18.0.0/15   comment="$ConfigVerNew"
/ip firewall add list=ipv4_private address=192.0.0.0/24    comment="$ConfigVerNew"
/ip firewall add list=ipv4_private address=192.0.2.0/24    comment="$ConfigVerNew"
/ip firewall add list=ipv4_private address=198.51.100.0/24 comment="$ConfigVerNew"
/ip firewall add list=ipv4_private address=203.0.113.0/24  comment="$ConfigVerNew"
/ip firewall add list=ipv4_private address=100.64.0.0/10   comment="$ConfigVerNew"
/ip firewall add list=ipv4_private address=240.0.0.0/4     comment="$ConfigVerNew"
# Multicast
/ip firewall add list=ipv4_private address=224.0.0.0/4     comment="$ConfigVerNew" list=ipv4_private
# RFC3068 -  6to4 relay Anycast
/ip firewall add list=ipv4_private address=192.88.99.0/24  comment="$ConfigVerNew" list=ipv4_private

:put "    Restoring NAT service on internet interface"
/ip firewall nat add chain=srcnat out-interface-list=internet ipsec-policy=out,none action=masquerade comment="$ConfigVerNew"


:put "    Setting up new filters"

# --- IPv4 protection for router itself, input chain
# accept established stuff but drop invalid state (keep untracked to boost IPSec)
/ip firewall filter add chain=input action=accept connection-state=established,related,untracked comment="$ConfigVerNew" 
# permit all stuff from LAN, though
/ip firewall filter add chain=input action=accept in-interface-list=intranet comment="$ConfigVerNew" 
# all the rest, drop
/ip firewall filter add chain=input action=drop comment="$ConfigVerNew" 

# --- IPv4 protection for LAN, forward chain




:put "    Removing temporary defensive filters"
/ip firewall filter remove numbers=[find where comment="temporary fence"]