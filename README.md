# Clearwater
Onboarding vIMS Clearwter from MetaSwitch with Cloudify, a TOSCA based VNF Orchestrator and policy engine.
Here is a link [Cloudify full life cycle video] (http://www.youtube.com/embed/ZsT78d1BR5s?enablejsapi=1&wmode=opaque to a video describing the full LCM (life cycle management)) from deployment, configuration, monitoring to healing/scaling corrective acctions and remediation. Upload clearwater51.yaml under the yaml directory, create a deployment and execute it.

This repository includes the following:

1. A TOSCA Blueprints to on-board Clearwater on OpenStack and VMWare vCloud Director, Clearwater51.yaml and Clearwater-vcloud.yaml
2. A DNS plugin to point each node (Bono, Ellis, Homer, Homestead, Sprout and Ralf) to the deployed DNS
3. Scripts to install the application stack on each node.
4. Relationships and dependencies are expressed in the TOSCA blueprint YAML file.

The blueprint supports healing, e.g you can kill Bono and a new VM would be instantiated and the application stack is installed on it including relationships to other nodes.



Step 1:
To upload the blueprint to the manager run the following command from CFY

CFY blueprints upload -b <blueprint name> -p clearwter51.yaml


Step 2:
To create a deployment type the following from CFY

CFY deployments create - <blueprint name> -d <deployment name>


Step 3:
Tp create a running execution  type the following in CFY

CFY executions start -d <deployment name> -w install

Step 4:

To delete a running executions type the following in CFY

CFY executions start -d <deployment name> -w uninstall

The following picture shows a running deployment example as it appears in the GUI


