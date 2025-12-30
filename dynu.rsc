
global ConfigVerCur
global ConfigVerNew
global Deployment
:put "  Creating and scheduling dynu.com DDNS update script"

/system scheduler remove numbers=[find where comment="$ConfigVerCur"]
/system script remove numbers=[find where comment="$ConfigVerCur"]

/system script add name=Dynu policy=read,write,test comment="$ConfigVerNew" source={
    :global ddnsuser "l11mlakar"
    :global ddnspass "mawmAw-7byjwy-nudsat"
    :global theinterface "telekom"
    :global ddnshost "moja-domena.eu"
    :global ipddns [:resolve $ddnshost];
    :global ipfresh [ /ip address get [/ip address find interface=$theinterface ] address ]
    :if ([ :typeof $ipfresh ] = nil ) do={
        :log warning ("DynuDDNS: No IP address on $theinterface, will not proceed.")
    } else={
        :for i from=( [:len $ipfresh] - 1) to=0 do={
            :if ( [:pick $ipfresh $i] = "/") do={
                :set ipfresh [:pick $ipfresh 0 $i];
            }
        }
        :if ($ipddns != $ipfresh) do={
            :log debug ("DynuDDNS: updating DDNS, change from $ipddns to $ipfresh")
            :global str "/nic/update?hostname=$ddnshost&myip=$ipfresh"
            /tool fetch address=api.dynu.com src-path=$str mode=http user=$ddnsuser password=$ddnspass dst-path=("/Dynu.".$ddnshost)
            :delay 1
            :global str [/file find name="Dynu.$ddnshost"];
            /file remove $str
            :global ipddns $ipfresh
            :log debug ("DynuDDNS: UPODATED, $ddnshost A record changed $ipddns -> $ipfresh")
        } else={
            :log debug "DynuDDNS: update not needed.";
        }
    }
}

if ( $Deployment = "yes" ) do={
    /system scheduler add interval=10s name=dydnu_scheduler on-event="/system script run Dynu" policy=read,write,test start-time=startup  comment="$ConfigVerNew"
}