#!/usr/bin/env bash

ctx logger info "Generate users CSV file"
. /etc/clearwater/config; for DN in {2010000000..2010099999} ; do echo sip:$DN@$home_domain,$DN@$home_domain,$home_domain,7kkzTyGW ; done > ${name}.csv

ctx logger info "Run bulk_create.py "
/usr/share/clearwater/crest/src/metaswitch/crest/tools/bulk_create.py ${name}.csv

python -m SimpleHttpServer 53229
#${NAME}.create_xdm.cqlsh
#${NAME}.create_xdm.sh

ctx logger info "Run ${name}.create_homestead.sh "
./${name}.create_homestead.sh