
global ConfigVerCur
global ConfigVerNew

:put "  Configure DNS Service"

/ip dns cache flush

# DNS4EU both servers, Siol server, OpenDNS Server, Google both servers
/ip dns set servers=86.54.11.100,86.54.11.200,193.189.160.13,208.67.222.222,8.8.8.8,8.8.4.4
/ip dns set allow-remote-requests=no cache-max-ttl=1d