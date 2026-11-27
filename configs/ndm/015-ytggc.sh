#!/bin/sh
[ "$type" = "ip6tables" ] && exit 0
[ "$table" != "filter" ] && exit 0
[ -x /opt/etc/init.d/S99ytggc ] && /opt/etc/init.d/S99ytggc start >/dev/null 2>&1
exit 0
