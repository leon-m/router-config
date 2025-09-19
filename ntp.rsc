global RedZoneNetwork
global GreenZoneNetwork
global BlueZoneNetwork
global step

:put "Step $step. Configure NTP Service"
# === Cleanup
/system ntp client servers remove numbers=[find where comment="configured by config script"]

/system ntp client set enabled=yes
/system ntp client servers add address=pool.ntp.org comment="configured by config script"
/system ntp server set enabled=yes multicast=yes manycast=yes broadcast=yes broadcast-addresses="$RedZoneNetwork.255,$BlueZoneNetwork.255,$GreenZoneNetwork.255"
