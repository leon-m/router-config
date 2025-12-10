global RedZoneNetwork
global GreenZoneNetwork
global BlueZoneNetwork

global ConfigVerCur
global ConfigVerNew

:put "  Configure NTP Service"
# === Cleanup
/system ntp client servers remove numbers=[find where comment="$ConfigVerCur"]

/system ntp client set enabled=yes
/system ntp client servers add address=pool.ntp.org comment="$ConfigVerNew"
/system ntp server set enabled=yes multicast=yes manycast=yes broadcast=yes broadcast-addresses="$RedZoneNetwork.255,$BlueZoneNetwork.255,$GreenZoneNetwork.255"
