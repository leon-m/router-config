global RedZoneNetwork   "192.168.13"
global RedZoneIp        "$RedZoneNetwork.1"
global RedZonePool      "$RedZoneNetwork.2-$RedZoneNetwork.254"
global GreenZoneNetwork "192.168.15"
global GreenZoneIp      "$GreenZoneNetwork.1"
global GreenZonePool    "$GreenZoneNetwork.2-$GreenZoneNetwork.254"
global BlueZoneNetwork  "192.168.17"
global BlueZoneIp       "$BlueZoneNetwork.1"
global BlueZonePool     "$BlueZoneNetwork.2-$BlueZoneNetwork.254"
global step             0
global Zones            { "zone-red"; "zone-blue"; "zone-green" }

# --- Bridges, interafces
set step ($step + 1)
import layout.rsc

# --- Bridges, interafces
set step ($step + 1)
import dhcp.rsc

# --- NTP stuff
set step ($step + 1)
import ntp.rsc

# --- DNS stuff
set step ($step + 1)
:import dns.rsc

# --- DNS stuff
set step ($step + 1)
:import isp.rsc
