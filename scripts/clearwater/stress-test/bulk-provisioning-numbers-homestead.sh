#!/usr/bin/env bash

ctx logger info "Generate users CSV file"
START=2010000000
END=$(($START + $number_of_subscribers))
. /etc/clearwater/config; for DN in $(eval echo "{$START..$END}") ; do echo sip:$DN@$home_domain,$DN@$home_domain,$home_domain,7kkzTyGW ; done > ${name}.csv

ctx logger info "Run bulk_create.py "
/usr/share/clearwater/crest/src/metaswitch/crest/tools/bulk_create.py ${name}.csv

python -m SimpleHTTPServer 53229 &
#${NAME}.create_xdm.cqlsh
#${NAME}.create_xdm.sh

ctx logger info "Run ${name}.create_homestead.sh "
bash ${name}.create_homestead.sh