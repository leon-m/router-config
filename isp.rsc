
global ConfigVerCur
global ConfigVerNew
global step

:put "Step $step. ISP Service Configuration"

# Use DHCP client if Telekom's modem does PPPoE, otherwise configure PPPoE
#/interface ethernet set [ find default-name=ether2 ] name=telekom
#/ip dhcp-client set use-peer-dns=no use-peer-ntp=no disabled=no telekom

/interface pppoe-client remove numbers=[find where comment="$ConfigVerCur"]
/interface pppoe-client add interface=WAN name=telekom user=mlx password=red95bar disabled=no use-peer-dns=no comment="$ConfigVerNew"

