#
# Default configuration to be applied after configuration reset
#
/port set 0 name=serial0
/port set 1 name=serial1

/ip neighbor discovery-settings set discover-interface-list=!dynamic
/system note set show-at-login=no
/system routerboard settings set enter-setup-on=delete-key
/system clock set time-zone-name=Europe/Ljubljana

# === Admin port set to ether10 and runs DHCP server
/ip pool add name=admin-pool ranges=192.168.77.2-192.168.77.254

/interface ethernet set [ find default-name=ether1 ] name=admin

/ip address add address=192.168.77.1/24 comment="Admin port IP address" interface=admin network=192.168.77.0
/ip dhcp-server add address-pool=admin-pool interface=admin lease-time=1d name=admin-dhcp
/ip dhcp-server network add address=192.168.77.0/24 dns-server=8.8.8.8 gateway=192.168.77.1
