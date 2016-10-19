[![Build Status](https://circleci.com/gh/cloudify-examples/clearwater-nfv-blueprint.svg?style=shield&circle-token=:circle-token)](https://circleci.com/gh/cloudify-examples/clearwater-nfv-blueprint)

# TOSCA Based Deployment and Monitoring of Clearwater vIMS

This repository contains a [Cloudify](http://getcloudify.org) blueprint for deploying MetaSwitch Clearwater vIMS Cloudify, a TOSCA based VNF Orchestrator and policy engine.
[This video](https://youtu.be/ZsT78d1BR5s) shows how the bluerint is used for deployment, configuration, monitoring and healing/scalingof Clearwater. 

## Clearwater Documentation

Some parts of this blueprint are based on the project Clearwater [documentation](https://clearwater.readthedocs.io/en/stable/index.html).

* Security Group Port Mappings were taken from [here](https://clearwater.readthedocs.io/en/stable/Clearwater_IP_Port_Usage.html).

## Repository Contents
This repository includes the following:

1. A TOSCA blueprint to deploy Clearwater on OpenStack including relationships and dependencies between the various Clearwater components.
2. A DNS plugin to point each node (Bono, Ellis, Homer, Homestead, Sprout and Ralf) to the deployed DNS
3. Scripts to install the application stack on each node


The blueprint supports healing, e.g you can kill Bono and as a result a new VM would be instantiated and the Bono application stack will be installed on it. The relationships to other nodes will make sure that these nodes are also wired properly with the newly created Bono VM. 

## Using the Blueprint
#### Step 0 
[Install the Cloudify CLI](http://docs.getcloudify.org/3.3.0/intro/installation/) and [bootstrap a Cloudify manager](http://docs.getcloudify.org/3.3.0/manager/bootstrapping/). 

#### Step 1
Upload the blueprint to the manager using the following command: 
```
cfy blueprints upload -b clearwater -p openstack-blueprint.yaml
```

#### Step 2
Create a deployment using the following command:
```
cfy deployments create -b clearwater -d clearwater
```

#### Step 3 
Invoke the `install` workflow: 
```
cfy executions start -d clearwater -w install
```

#### Make a phone call with Jitsi

There are many clients that you can use with SIP, but these instructions are for the Jitsi client.

1. Download the [Jitsi client](https://jitsi.org/Main/Download).
2. Get the IP of Ellis, the IP of Bono, and the signup_code from `cfy deployments outputs -d clearwater`.
3. Open the IP of Ellis in a browser and signup for an account using the signup_code.
4. When you sign up you should see the Clearwater dashboard with your SIP ID and password. Save them.
5. Open the preferences of the Jitsu Client.
6. Fill out the Account section with your SIP ID (including the '@example.com') and password from step 4.
7. Open the Connection tab. Put the IP of Bono from step 2 in the proxy field. Use port 5060. Preferred Transport TCP.
8. Repeat these steps on another computer.

If everthing worked, you should be able to make phone calls between the two computers.

#### Uninstalling
To uninstall and delete the running deployment, invoke the `uninstall` workflow: 
```
cfy executions start -d clearwater -w uninstall
```

The following picture shows a running deployment example as it appears in the GUI
![alt text](https://github.com/cloudify-examples/clearwater-scripts-plugin-blueprint/blob/master/yaml/images/Clearwater.jpg "ClearWater Deployment")

