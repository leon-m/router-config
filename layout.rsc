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

:put "Step $step. Configurating Bridges and Interfaces"
:put "    Cleaning up lingering configuration"
:foreach zone in=$Zones do={
    /ip address remove numbers=[find where interface=$zone]
    /interface bridge port remove numbers=[find bridge=$zone]
    /interface bridge remove numbers=[find where name=$zone]
}
/interface/list/member remove numbers=[find where name=intranet]
/interface/list remove numbers=[find where name=intranet]
/interface/list/member remove numbers=[find where name=internet]
/interface/list remove numbers=[find where name=internet]
/interface/list/member remove numbers=[find where name=guest]
/interface/list remove numbers=[find where name=guest]


# --- Bridges and layout
:put "    Creating bridges for zones"
/interface ethernet set [ find default-name=ether2 ] name=WAN
/interface bridge add comment="Leon zone" name=zone-red
/interface bridge add comment="Urska zone" name=zone-blue
/interface bridge add comment="Guest Zone" name=zone-green
/interface bridge port add bridge=zone-green interface=ether3
/interface bridge port add bridge=zone-blue  interface=ether4
/interface bridge port add bridge=zone-red   interface=ether6
/interface bridge port add bridge=zone-red   interface=ether7
/interface bridge port add bridge=zone-red   interface=ether8

:put "    Setting up interface lists"
/interface/list add name=intranet
/interface/list add name=internet
/interface/list add name=guest

/interface/list/member add list=intranet interface=zone-red
/interface/list/member add list=intranet interface=zone-blue
/interface/list/member add list=intranet interface=zone-green
/interface/list/member add list=guest interface=zone-green

# --- Static IP Addresses
:put "    Assigning static IP addresses"
/ip address add address="$RedZoneIp/24" comment="Red router" interface=zone-red network="$RedZoneNetwork.0"
/ip address add address="$BlueZoneIp/24" comment="Blue router" interface=zone-blue network="$BlueZoneNetwork.0"
/ip address add address="$GreenZoneIp/24" comment="Green router" interface=zone-green network="$GreenZoneNetwork.0"

