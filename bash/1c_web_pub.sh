#!/bin/bash

wwwdir=/var/www/1c/$2
mkdir -p $wwwdir
touch /etc/apache2/conf-available/$2.conf
/opt/1cv8/x86_64/$1/webinst -apache24 -wsdir $2 -dir "$wwwdir" -connstr "Srvr='localhost';Ref='$3';" -confPath /etc/apache2/conf-available/$2.conf
systemctl reload apache2
a2enconf $2 && echo
systemctl reload apache2
