#!/bin/bash -e

ctx logger debug "${COMMAND}"

ctx logger info "Configure the APT software source"
if [ ! -f /etc/apt/sources.list.d/clearwater.list ]
  then
    echo 'deb http://repo.cw-ngv.com/stable binary/' | sudo tee --append /etc/apt/sources.list.d/clearwater.list
    curl -L http://repo.cw-ngv.com/repo_key | sudo apt-key add -
fi
sudo apt-get update

ctx logger info ""

sudo /etc/clearwater/local_config


ctx logger info "Installing stress test package"
sudo DEBIAN_FRONTEND=noninteractive apt-get install clearwater-sip-stress --yes --force-yes -o DPkg::options::=--force-confnew
ctx logger info "The installation packages is done correctly"