#!/bin/bash -e

kill_if_timeout() {
  if [ $? -ne 0 ]; then
      sudo pkill -9 apt-get
      exit 1
  fi
}

ctx logger debug "${COMMAND}"

ctx logger info "Configure the APT software source"
if [ ! -f /etc/apt/sources.list.d/clearwater.list ]
  then
    echo 'deb http://repo.cw-ngv.com/archive/repo107 binary/' | sudo tee --append /etc/apt/sources.list.d/clearwater.list
    curl -L http://repo.cw-ngv.com/repo_key | sudo apt-key add -
fi
sudo apt-get update

ctx logger info "Installing ellis packages and other clearwater packages"
timeout 5m sudo DEBIAN_FRONTEND=noninteractive apt-get install ellis --yes --force-yes -o DPkg::options::=--force-confnew
kill_if_timeout
timeout 5m sudo DEBIAN_FRONTEND=noninteractive apt-get install clearwater-management --yes --force-yes
kill_if_timeout
ctx logger info "The installation packages is done correctly"

ctx logger info "Configure a new DNS server"
echo 'RESOLV_CONF=/etc/dnsmasq.resolv.conf' | sudo tee --append  /etc/default/dnsmasq
sudo service dnsmasq force-reload
