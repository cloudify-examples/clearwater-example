#!/bin/bash

# This is needed to make the SNMP diamond collector work. Working with 1.3.3 cloudify-diamond-plugin.
# Later versions cause problems at the moment - they use pretty print instead of print so the collector 
# compare pretty printed oir with the actual oid that never match.
pip install pysnmp==4.2.5

