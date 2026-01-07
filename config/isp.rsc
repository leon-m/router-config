
global ConfigVerCur
global ConfigVerNew
global Deployment

:put "  ISP Service Configuration"

# Use DHCP client if Telekom's modem does PPPoE, otherwise configure PPPoE
#/interface ethernet set [ find default-name=ether2 ] name=telekom
#/ip dhcp-client set use-peer-dns=no use-peer-ntp=no disabled=no telekom

/interface pppoe-client remove numbers=[find where comment="$ConfigVerCur"]

:if ( $Deployment = "yes" ) do={
    /interface pppoe-client add interface=WAN name=telekom user=mlx password=red95bar disabled=no use-peer-dns=no add-default-route=yes comment="$ConfigVerNew"
} else={
    # for development WAN port runs on the fixed IP address 192.168.3.3 and accepts all connections
    /ip address add address=192.168.3.3/24 comment="$ConfigVerCur" interface=WAN network=192.168.3.0
}
