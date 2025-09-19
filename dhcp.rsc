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

:put "Step $step. Configuring per-zone DHCP services"
:put "    Cleaning up lingering configuration"
:foreach zone in=$Zones do={
    /ip dhcp-server lease remove numbers=[find where server=$zone]
    /ip dhcp-server network remove numbers=[find where comment="$zone"] 
    /ip dhcp-server remove numbers=[find where name=$zone]
    /ip pool remove numbers=[find name=$zone]
}

:put "    Creating and configuring DHCP address pools and servers"
/ip pool add name=zone-red ranges=$RedZonePool
/ip pool add name=zone-blue ranges=$BlueZonePool
/ip pool add name=zone-green ranges=$GreenZonePool
/ip dhcp-server add address-pool=zone-red interface=zone-red lease-time=1d name=zone-red
/ip dhcp-server add address-pool=zone-blue interface=zone-blue lease-time=1d name=zone-blue
/ip dhcp-server add address-pool=zone-green interface=zone-green lease-time=1d name=zone-green
/ip dhcp-server network add address="$RedZoneNetwork.0/24" dns-server="$RedZoneNetwork.99" gateway=$RedZoneIp comment="zone-red" ntp-server=$RedZoneIp
/ip dhcp-server network add address="$BlueZoneNetwork.0/24" dns-server=$BlueZoneIp gateway=$BlueZoneIp comment="zone-blue" ntp-server=$BlueZoneIp
/ip dhcp-server network add address="$GreenZoneNetwork.0/24" dns-server=$GreenZoneIp gateway=$GreenZoneIp comment="zone-green" ntp-server=$GreenZoneIp

:put  "    Adding static leases"
/ip dhcp-server lease add address="$RedZoneNetwork.20" mac-address=20:CF:30:B1:C5:CA server=zone-red
/ip dhcp-server lease add address="$RedZoneNetwork.71" mac-address=C4:2C:03:10:A3:C5 server=zone-red
/ip dhcp-server lease add address="$RedZoneNetwork.72" client-id=Omega-247D mac-address=40:A3:6B:C7:24:7E server=zone-red
/ip dhcp-server lease add address="$RedZoneNetwork.73" mac-address=DC:A6:32:71:3A:F8 server=zone-red
/ip dhcp-server lease add address="$RedZoneNetwork.74" client-id=bbone-ai mac-address=28:EC:9A:4C:A7:0A server=zone-red
/ip dhcp-server lease add address="$RedZoneNetwork.75" client-id=dell-42 mac-address=00:E0:4C:40:05:13 server=zone-red
/ip dhcp-server lease add address="$RedZoneNetwork.111" client-id=Printer mac-address=D8:9C:67:C0:35:F7 server=zone-red
/ip dhcp-server lease add address="$RedZoneNetwork.70" client-id=macbook-42 mac-address=00:E0:4C:97:20:77 server=zone-red
/ip dhcp-server lease add address="$RedZoneNetwork.55" client-id=dell-42 mac-address=38:C9:86:F1:84:A9 server=zone-red
/ip dhcp-server lease add address="$RedZoneNetwork.76" client-id=ibst-dev-2 mac-address=8C:16:45:64:F5:23 server=zone-red
/ip dhcp-server lease add address="$RedZoneNetwork.99" client-id=NAS mac-address=00:11:32:7F:42:6B server=zone-red
/ip dhcp-server lease add address="$BlueZoneNetwork.30" client-id=media mac-address=DC:A6:32:71:3A:F9 server=zone-blue
/ip dhcp-server lease add address="$BlueZoneNetwork.52" mac-address=5C:E9:31:7E:62:17 server=zone-blue
/ip dhcp-server lease add address="$BlueZoneNetwork.72" client-id=Omega-247D mac-address=40:A3:6B:C7:24:7F server=zone-blue
/ip dhcp-server lease add address="$GreenZoneNetwork.72" client-id=Omega-247D mac-address=40:A3:6B:C7:24:7F server=zone-green

