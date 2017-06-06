[![Build Status](https://circleci.com/gh/cloudify-examples/clearwater-nfv-blueprint.svg?style=shield&circle-token=:circle-token)](https://circleci.com/gh/cloudify-examples/clearwater-nfv-blueprint)

# Clearwater NFV Blueprint

This repository contains a [Cloudify](http://getcloudify.org) blueprint for deploying MetaSwitch Clearwater vIMS Cloudify, a TOSCA based VNF Orchestrator and policy engine.
[This video](https://youtu.be/ZsT78d1BR5s) shows how the bluerint is used for deployment, configuration, monitoring and healing/scalingof Clearwater. 


## prerequisites

You will need a *Cloudify Manager* running in either AWS, Azure, or Openstack.

If you have not already, set up the [example Cloudify environment](https://github.com/cloudify-examples/cloudify-environment-setup). Installing that blueprint and following all of the configuration instructions will ensure you have all of the prerequisites, including keys, plugins, and secrets.


### Execute Install

Next you provide those inputs to the blueprint and execute install:


#### For AWS run:

```shell
$ cfy install \
    https://github.com/cloudify-examples/clearwater-nfv-blueprint/archive/4.0.1.1.zip \
    -b clr \
    -n aws-blueprint.yaml
```


#### For Azure run:

```shell
$ cfy install \
    https://github.com/cloudify-examples/clearwater-nfv-blueprint/archive/4.0.1.1.zip \
    -b clr \
    -n azure-blueprint.yaml
```


#### For Openstack run:

```shell
$ cfy install \
    https://github.com/cloudify-examples/clearwater-nfv-blueprint/archive/4.0.1.1.zip \
    -b clr \
    -n openstack-blueprint.yaml
```


## Clearwater Documentation

Some parts of this blueprint are based on the project Clearwater [documentation](https://clearwater.readthedocs.io/en/stable/index.html).

* Security Group Port Mappings were taken from [here](https://clearwater.readthedocs.io/en/stable/Clearwater_IP_Port_Usage.html).

## Repository Contents
This repository includes the following:

1. A TOSCA blueprint to deploy Clearwater on OpenStack, AWS and vSphere including relationships and dependencies between the various Clearwater components.
2. A DNS plugin to point each node (Bono, Ellis, Homer, Homestead, Sprout and Ralf) to the deployed DNS
3. Scripts to install the application stack on each node

The blueprint supports healing, e.g you can kill Bono and as a result a new VM would be instantiated and the Bono application stack will be installed on it. The relationships to other nodes will make sure that these nodes are also wired properly with the newly created Bono VM.


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

