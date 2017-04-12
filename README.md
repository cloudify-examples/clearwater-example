[![Build Status](https://circleci.com/gh/cloudify-examples/clearwater-nfv-blueprint.svg?style=shield&circle-token=:circle-token)](https://circleci.com/gh/cloudify-examples/clearwater-nfv-blueprint)

# TOSCA Based Deployment and Monitoring of Clearwater vIMS

This repository contains a [Cloudify](http://getcloudify.org) blueprint for deploying MetaSwitch Clearwater vIMS Cloudify, a TOSCA based VNF Orchestrator and policy engine.
[This video](https://youtu.be/ZsT78d1BR5s) shows how the bluerint is used for deployment, configuration, monitoring and healing/scalingof Clearwater. 

## Clearwater Documentation

Some parts of this blueprint are based on the project Clearwater [documentation](https://clearwater.readthedocs.io/en/stable/index.html).

* Security Group Port Mappings were taken from [here](https://clearwater.readthedocs.io/en/stable/Clearwater_IP_Port_Usage.html).

## Repository Contents
This repository includes the following:

1. A TOSCA blueprint to deploy Clearwater on OpenStack, AWS and vSphere including relationships and dependencies between the various Clearwater components.
2. A DNS plugin to point each node (Bono, Ellis, Homer, Homestead, Sprout and Ralf) to the deployed DNS
3. Scripts to install the application stack on each node

The blueprint supports healing, e.g you can kill Bono and as a result a new VM would be instantiated and the Bono application stack will be installed on it. The relationships to other nodes will make sure that these nodes are also wired properly with the newly created Bono VM. 

## AWS
This blueprint assumes a network architecture that includes a private and public network in a single VPC, like the [AWS VPC Scenario 2](http://docs.aws.amazon.com/AmazonVPC/latest/UserGuide/VPC_Scenario2.html).
See [AWS Example Blueprint](https://github.com/cloudify-examples/aws-azure-openstack-blueprint/tree/master/aws)
All nodes connected to an elastic ip will be contained in the public subnet (Bono and Ellis) and all nodes with no elastic ip will be contained in the private subnet (Homer, Homestead, Sprout and Ralf).

#### Inputs
`existing_vpc_id` is the manager's vpc id.
`existing_public_subnet_id` is the manager's public subnet id.
`existing_private_subnet_id` is the manager's private subnet id.

## Azure
If you do not already have a key pair on your Azure manager, you can create one using the [rsa-key-blueprint](https://raw.githubusercontent.com/cloudify-examples/cloudify-key-plugin/master/examples/rsa-key-blueprint.yaml).
Use the private key path to populate your azure_agent_key_file input and your outputs to populate the key data in the vm_os_pubkeys input.

#### Inputs
`azure_agent_key_file` is the pre installed key on the manager.
`mgr_resource_group_name` is the manager's resource group name.
`mgr_virtual_network_name` is the manager's virtual network name.
`mgr_subnet_name` is the manager's subnet name.

## Using the Blueprint
#### Step 0 
[Install the Cloudify CLI](http://docs.getcloudify.org/3.3.0/intro/installation/) and [bootstrap a Cloudify manager](http://docs.getcloudify.org/3.3.0/manager/bootstrapping/). 

#### Install

```
cfy install openstack-blueprint.yaml -i inputs/aws.yaml.example -p clearwater
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
cfy uninstall clearwater
```

The following picture shows a running deployment example as it appears in the GUI
![alt text](https://github.com/cloudify-examples/clearwater-scripts-plugin-blueprint/blob/master/yaml/images/Clearwater.jpg "ClearWater Deployment")

