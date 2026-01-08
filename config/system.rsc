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
if ([/system/logging/action/find name=LogToNas]) do={
    /system logging action remove numbers=[find where name=LogToNas]
    /system logging remove numbers=[find invalid]
}

# first, info logs are not necessary
system logging disable numbers=[find where topics~"info"]
# now configure remote logs for what could be hacking attepmts
/system logging action add name="LogToNas" target=remote remote=192.168.3.99 remote-port=7318 src-address=192.168.3.1 bsd-syslog=no syslog-time-format=bsd-syslog syslog-facility=daemon syslog-severity=notice
/system logging add action=LogToNas topics=firewall
