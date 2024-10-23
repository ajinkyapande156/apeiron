#!/bin/bash

# Handy for casual API usage without worrying about certs.

host=$1
type=${2:-http}

ssh root@$host </dev/null <<EOF
    set -x
    sed -i -e 's+proto: http.*$+proto: $type+' \
        -e 's+client_authn: true+client_authn: false+' \
        -e 's+client_authz: true+client_authz: false+' \
        /etc/ahv-gateway/config/ahv_gateway.yaml
    systemctl restart ahv-gateway
EOF