#!/usr/bin/env bash
ctx logger info "Remove all data from /tmp/cloudify-ctx/work/${name}"
rm -f /tmp/cloudify-ctx/work/${name}.*
