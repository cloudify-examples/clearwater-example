import sys
from cloudify_rest_client import CloudifyClient
from influxdb.influxdb08 import InfluxDBClient
from influxdb.influxdb08.client import InfluxDBClientError
import json 
from os import utime
from os import getpid 
from os import path
import time
import datetime

# check against influxdb which nodes are available CPUtotal
# autoheal only missing nodes comparing to the node_instances that are taken from cloudify
# do it only for compute nodes

def cooldown():
    if path.isfile('/home/ubuntu/cooldown'):  
        now = datetime.datetime.now()
        then = datetime.datetime.fromtimestamp(path.getmtime('/home/ubuntu/cooldown'))
        tdelta = now - then
        seconds = tdelta.total_seconds()
        if (seconds < 420):
           return True
    else:
        pass
    return False

def check_heal(nodes_to_monitor,depl_id):
    if cooldown():
       print('Exiting...\n')
       exit(0)
    c = CloudifyClient('localhost')
    c_influx = InfluxDBClient(host='localhost', port=8086, database='cloudify')
    f=open('/home/ubuntu/logfile','w')
    f.write('in check heal\n')
    c = CloudifyClient('localhost')
    # compare influx data (monitoring) to cloudify desired state

    for node_name in nodes_to_monitor:
        instances=c.node_instances.list(depl_id,node_name)
#        f.write('instances{0}\n'.format(instances))
        for instance in instances:
            q_string='SELECT MEAN(value) FROM /' + depl_id + '\.' + node_name + '\.' + instance.id + '\.cpu_total_system/ GROUP BY time(10s) '\
                     'WHERE  time > now() - 40s'
            f.write('query string is{0}\n'.format(q_string))
            try:
               result=c_influx.query(q_string)
               f.write('result is {0} \n'.format(result))
               if not result:
                open('/home/ubuntu/cooldown','a').close()
                utime('/home/ubuntu/cooldown',None)
                execution_id=c.executions.start(depl_id,'heal',{'node_id': instance.id})
            except InfluxDBClientError as ee:
               f.write('DBClienterror {0}\n'.format(str(ee)))
               f.write('instance id is {0}\n'.format(instance))   
            except Exception as e:
               f.write(str(e))
#               check_heal(nodes_to_monitor,depl_id)

def main(argv):
    of = open('/home/ubuntu/pid_file', 'w')
    of.write('%i' % getpid())
    of.close()
    for i in range(len(argv)):
       print ("argv={0}\n".format(argv[i]))
    nodes_to_monitor=json.loads(argv[1].replace("'", '"'))
    depl_id=argv[2]
    print ("nodes={0}\n".format(nodes_to_monitor))
    check_heal(nodes_to_monitor, depl_id)

if __name__ == '__main__':
    main(sys.argv)
