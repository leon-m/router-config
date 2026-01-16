global RedZoneNetwork
global RedZoneIp
global RedZonePool
global GreenZoneNetwork
global GreenZoneIp
global GreenZonePool
global BlueZoneNetwork
global BlueZoneIp
global BlueZonePool
global Zones
global ConfigVerCur
global ConfigVerNew


:put "  Configuring System Stuff"
:put "    Configuring logging subsystem"

system logging remove numbers=[find where topics~"(dhcp;info|info;dhcp)"]
system logging remove numbers=[find where topics~"(account;info|info;account)"]
system logging remove numbers=[find where topics~"(ssh;info|info;ssh)"]
system logging remove numbers=[find where topics~"(system;info|info;system)"]
system logging remove numbers=[find where topics~"firewall"]

# first, info logs are not necessary so disqble them
system logging disable numbers=[find where topics~"info"]
# but keep few info leve stuff reardless
system logging add topics=dhcp,info action=memory
system logging add topics=account,info action=memory
system logging add topics=ssh,info action=memory
system logging add topics=system,info action=memory

# now configure remote logs for what could be hacking attepmts
/system/logging/action/set numbers=[find where name=remote] target=remote remote=192.168.3.99 remote-port=7318 src-address=192.188.3.1 bsd-syslog=no syslog-time-format=bsd-syslog syslog-facility=daemon syslog-severity=auto
system logging add topics=firewall action=remote