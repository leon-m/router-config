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

:put "    Address lists"
/ip firewall address-list remove numbers=[find where comment="$ConfigVerCur"]
/ip firewall address-list add list=intranet address=$RedZonePool comment="$ConfigVerNew"
/ip firewall address-list add list=intranet address=$BlueZonePool comment="$ConfigVerNew"
/ip firewall address-list add list=intranet address=$GreenZonePool comment="$ConfigVerNew"

:put "    Setting up temporary defensive filters"
/ip firewall filter add chain=input action=drop in-interface-list=!intranet comment="temporary fence"
/ip firewall filter add chain=input action=drop in-interface-list=!intranet comment="temporary fence"

:put "    NAT service on internet interface"
/ip firewal nat remove numbers=[find where comment="$ConfigVerCur"]
/ip firewall nat add chain=srcnat out-interface-list=internet ipsec-policy=out,none action=masquerade comment="$ConfigVerNew"

:put "    Removing filters from old configuration"
/ip firewal filter remove numbers=[find where comment="$ConfigVerCur"]

:put "    Setting up new filters"

:put "    Removing temporary defensive filters"
/ip firewall filter remove numbers=[find where comment="temporary fence"]