#!/usr/bin/env bash

ctx logger info "Downloading create_xdm files"
wget ${homestead_ip}:53229/${name}.create_xdm.cqlsh
wget ${homestead_ip}:53229/${name}.create_xdm.sh
ctx logger info "Running ${name}.create_xdm.sh"
bash ${name}.create_xdm.sh
