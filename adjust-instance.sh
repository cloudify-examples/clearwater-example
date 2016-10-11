#!/bin/bash -e

# Order doesn't matter here, as we don't start the services - we're just enabling them for reboot.
service_names=(nginx.service cloudify-webui.service cloudify-restservice.service cloudify-mgmtworker.service \
    cloudify-riemann.service cloudify-rabbitmq.service cloudify-influxdb.service elasticsearch.service \
    cloudify-amqpinflux.service logstash.service)

private_ip=$1
echo "Enabling services"
for service in ${service_names[*]}
do
    echo "   Enabling $service"
    sudo systemctl enable $service
done

#echo "Adjusting hostname to ${manager_hostname}"
#sudo hostnamectl set-hostname ${manager_hostname}

echo "Adjusting private IP to ${private_ip}"

echo "Editing /etc/sysconfig/cloudify-mgmtworker..."
sudo sed -i -e "s/MANAGEMENT_IP=.*/MANAGEMENT_IP=\"$private_ip\"/" /etc/sysconfig/cloudify-mgmtworker
sudo sed -i -e "s#MANAGER_FILE_SERVER_URL=\"http://.*:53229\"#MANAGER_FILE_SERVER_URL=\"http://$private_ip:53229\"#" /etc/sysconfig/cloudify-mgmtworker
sudo sed -i -e "s#MANAGER_FILE_SERVER_BLUEPRINTS_ROOT_URL=\"http://.*:53229/blueprints\"#MANAGER_FILE_SERVER_BLUEPRINTS_ROOT_URL=\"http://$private_ip:53229/blueprints\"#" /etc/sysconfig/cloudify-mgmtworker

echo "Editing /etc/sysconfig/cloudify-amqpinflux..."
sudo sed -i -e "s/AMQP_HOST=.*/AMQP_HOST=\"$private_ip\"/" /etc/sysconfig/cloudify-amqpinflux
sudo sed -i -e "s/INFLUXDB_HOST=.*/INFLUXDB_HOST=\"$private_ip\"/" /etc/sysconfig/cloudify-amqpinflux

echo "Editing /etc/sysconfig/cloudify-riemann..."
sudo sed -i -e "s/RABBITMQ_HOST=.*/RABBITMQ_HOST=\"$private_ip\"/" /etc/sysconfig/cloudify-riemann
sudo sed -i -e "s/MANAGEMENT_IP=.*/MANAGEMENT_IP=\"$private_ip\"/" /etc/sysconfig/cloudify-riemann

echo "Editing /etc/logstash/conf.d/logstash.conf..."
sudo sed -i -e "s/host => \".*\"/host => \"$private_ip\"/" /etc/logstash/conf.d/logstash.conf

echo "Editing /opt/manager/cloudify-rest.conf..."
sudo sed -i -e "s/db_address: '.*'/db_address: '$private_ip'/" /opt/manager/cloudify-rest.conf
sudo sed -i -e "s#amqp_address: '.*:5672/'#amqp_address: '$private_ip:5672/'#" /opt/manager/cloudify-rest.conf

echo "Editing /opt/cloudify-ui/backend/gsPresets.json..."
sudo sed -i -e "s/\"host\": \".*\"/\"host\": \"$private_ip\"/" /opt/cloudify-ui/backend/gsPresets.json

echo "Editing /opt/mgmtworker/work/broker_config.json..."
sudo sed -i -e "s/\"broker_hostname\": \".*\"/\"broker_hostname\": \"$private_ip\"/" /opt/mgmtworker/work/broker_config.json

echo "Private IP adjustment done."

echo "Starting RabbitMQ..."
sudo systemctl start cloudify-rabbitmq.service

echo "RabbitMQ started, waiting 20 seconds to ensure it's up..."
sleep 20
echo "Deleting RabbitMQ guest user and existing Cloudify user, if any..."
set +e
sudo rabbitmqctl clear_permissions guest
sudo rabbitmqctl delete_user guest
sudo rabbitmqctl clear_permissions cloudify
sudo rabbitmqctl delete_user cloudify
set -e
echo "Adding Cloudify's user and setting permissions..."
sudo rabbitmqctl add_user cloudify c10udify
sudo rabbitmqctl set_permissions cloudify '.*' '.*' '.*'
echo "Stopping RabbitMQ..."
set +e
sudo systemctl stop cloudify-rabbitmq.service
rabbitmq_stop_rc=$?
echo "RabbitMQ stopped with return code $rabbitmq_stop_rc"
if [[ ($rabbitmq_stop_rc -ne 143) && ($rabbitmq_stop_rc -ne 0) ]]; then
    exit $rabbitmq_stop_rc
fi
set -e
echo "RabbitMQ stopped, waiting 10 seconds to ensure it's down..."
sleep 10
echo "All done."
