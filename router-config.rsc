global Deployment       "no"

global RedZoneNetwork
global GreenZoneNetwork
global BlueZoneNetwork
:if ( $Deployment = "yes" ) do={
    :set RedZoneNetwork   "192.168.3"
    :set GreenZoneNetwork "192.168.5"
    :set BlueZoneNetwork  "192.168.7"
} else={
    :set RedZoneNetwork   "192.168.13"
    :set GreenZoneNetwork "192.168.15"
    :set BlueZoneNetwork  "192.168.17"
}
global RedZoneIp        "$RedZoneNetwork.1"
global RedZonePool      "$RedZoneNetwork.2-$RedZoneNetwork.254"
global GreenZoneIp      "$GreenZoneNetwork.1"
global GreenZonePool    "$GreenZoneNetwork.2-$GreenZoneNetwork.254"
global BlueZoneIp       "$BlueZoneNetwork.1"
global BlueZonePool     "$BlueZoneNetwork.2-$BlueZoneNetwork.254"
global Zones            { "zone-red"; "zone-blue"; "zone-green" }
# When updating config set the ConfigVerOld  to the ConfigVer and
# move ConfigVer forward. The scripts will remove the necessary
# parts of previous configuration before applying new config
global ConfigVerCur     "config v0.1.0"
global ConfigVerNew     "config v0.1.0"

# ===================================================================
#
# Deployment checklist 
# 
# 1. Make sure that deployment variable above is set to "yes"
# 2. Make  sure that ConfigVerNew is different than ConfigVerCur

# --- Bridges, interafces
:put "Step 1: [layout.rsc]"
import layout.rsc

# --- Bridges, interafces
:put "Step 2: [dhcp.rsc]"
import dhcp.rsc

# --- Firewall stuff
:put "Step 3: [firewall.rsc]"
:import firewall.rsc

# --- NTP stuff
:put "Step 4: [ntp.rsc]"
import ntp.rsc

# --- DNS stuff
:put "Step 5: [dns.rsc]"
:import dns.rsc

# --- ISP stuff
:put "Step 6: [isp.rsc]"
:import isp.rsc

# --- DDNS update
:put "Step 7: [dynu.rsc]"
:import dynu.rsc
