global RedZoneNetwork
global RedZoneIp
global RedZonePool
global GreenZoneNetwork
global GreenZoneIp
global GreenZonePool
global BlueZoneNetwork
global BlueZoneIp
global BlueZonePool
global step
global Zones
global ConfigVerCur
global ConfigVerNew


:put "Step $step. Configurating Bridges and Interfaces"
:put "    Cleaning up current configuration"
#:foreach zone in=$Zones do={
#    /ip address remove numbers=[find where interface=$zone]
#    /interface bridge port remove numbers=[find bridge=$zone]
#    /interface bridge remove numbers=[find where name=$zone]
#}

/ip address remove numbers=[find where comment="$ConfigVerCur"]
/interface bridge port remove numbers=[find where comment="$ConfigVerCur"]
/interface bridge remove numbers=[find where comment="$ConfigVerCur"]
/interface/list/member remove numbers=[find where comment="$ConfigVerCur"]
/interface/list remove numbers=[find where comment="$ConfigVerCur"]

# --- Bridges and layout
:put "    Creating bridges for zones"

/interface bridge add comment="$ConfigVerNew" name=zone-red 
/interface bridge add comment="$ConfigVerNew" name=zone-blue
/interface bridge add comment="$ConfigVerNew" name=zone-green
/interface bridge port add bridge=zone-green interface=ether3 comment="$ConfigVerNew"
/interface bridge port add bridge=zone-blue  interface=ether4 comment="$ConfigVerNew"
/interface bridge port add bridge=zone-red   interface=ether6 comment="$ConfigVerNew"
/interface bridge port add bridge=zone-red   interface=ether7 comment="$ConfigVerNew"
/interface bridge port add bridge=zone-red   interface=ether8 comment="$ConfigVerNew"

:put "    Setting up interface lists"
/interface/list add name=internet comment="$ConfigVerNew"
/interface/list add name=intranet comment="$ConfigVerNew"
/interface/list add name=guest comment="$ConfigVerNew"

/interface list member add list=internet interface=WAN comment="$ConfigVerNew"
/interface/list/member add list=intranet interface=zone-red comment="$ConfigVerNew"
/interface/list/member add list=intranet interface=zone-blue comment="$ConfigVerNew"
/interface/list/member add list=intranet interface=zone-green comment="$ConfigVerNew"
/interface/list/member add list=guest interface=zone-green comment="$ConfigVerNew"

# --- Static IP Addresses
:put "    Assigning static IP addresses"
/ip address add address="$RedZoneIp/24"   comment="$ConfigVerNew" interface=zone-red   network="$RedZoneNetwork.0"
/ip address add address="$BlueZoneIp/24"  comment="$ConfigVerNew" interface=zone-blue  network="$BlueZoneNetwork.0"
/ip address add address="$GreenZoneIp/24" comment="$ConfigVerNew" interface=zone-green network="$GreenZoneNetwork.0"

