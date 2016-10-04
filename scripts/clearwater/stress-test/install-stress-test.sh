#!/bin/bash -e

ctx logger info "Configure the APT software source"
if [ ! -f /etc/apt/sources.list.d/clearwater.list ]
  then
    echo 'deb http://repo.cw-ngv.com/stable binary/' | sudo tee --append /etc/apt/sources.list.d/clearwater.list
    curl -L http://repo.cw-ngv.com/repo_key | sudo apt-key add -
fi
sudo apt-get update

ctx logger info ""

sudo tee -a /etc/clearwater/local_config << EOF
local_ip=${homestead_ip}
EOF

sudo tee -a /etc/clearwater/shared_config << EOF
home_domain=${home_domain}
bono_servers=[${bono_servers}]
count=${number_of_subscribers}
EOF

ctx logger info "Installing stress test package"
sudo DEBIAN_FRONTEND=noninteractive apt-get install clearwater-sip-stress --yes --force-yes -o DPkg::options::=--force-confnew
ctx logger info "The installation packages is done correctly"