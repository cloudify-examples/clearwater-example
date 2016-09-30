ctx logger info "starting DNS..."
# Install BIND.
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install bind9 --yes
# Update BIND configuration with the specified zone and key.
sudo bash -c 'cat >> /etc/bind/named.conf.local << EOF
key example.com. {
  algorithm "HMAC-MD5";
  secret "8r6SIIX/cWE6b0Pe8l2bnc/v5vYbMSYvj+jQPP4bWe+CXzOpojJGrXI7iiustDQdWtBHUpWxweiHDWvLIp6/zw==";
};


zone "example.com" IN {
  type master;
  file "/var/lib/bind/db.example.com";
  allow-update {
    key example.com.;
  };
};

zone "openstacklocal" {type master; file "/etc/bind/openstacklocal.local";};

EOF'

sudo bash -c 'cat > /etc/bind/openstacklocal.local << EOF
;
; BIND data file for local loopback interface
;
\$TTL    604800
@       IN      SOA     openstacklocal. root.openstacklocal. (
                           2         ; Serial
                          604800         ; Refresh
                          86400         ; Retry
                          2419200         ; Expire
                          604800 )       ; Negative Cache TTL
;
@       IN      NS      openstacklocal.
;@      IN      A       127.0.0.1
;@      IN      AAAA    ::1
EOF'

# zone configuration.
ctx logger info "DNS IP address is ${dns_ip}"
sudo echo ${dns_ip} > /home/ubuntu/dnsfile
sudo bash -c 'cat > /var/lib/bind/db.example.com<< EOF
; example.com
\$TTL 5m
\$ORIGIN example.com.

@               3600    IN SOA  ns.example.com. admin.example.com. (
                                2016040638 ; serial
                                86400      ; refresh (1 day)
                                7200       ; retry (2 hours)
                                604800     ; expire (1 week)
                                30         ; minimum (30 seconds)
                                )
@               3600    IN      NS      ns.example.com.

ns A $(hostname -I)
EOF'
sudo chown root:bind /var/lib/bind/db.example.com
# Now that BIND configuration is correct, kick it to reload.
sudo service bind9 reload
