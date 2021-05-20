# This should be run via ssh onto one of the compute instances

set -euxo pipefail

# These are the IP addresses assigned to couchdb in the docker-compose.yaml file
declare -ax nodes=(couch1. couch2. couch3.)
export masternode=`echo ${nodes} | cut -f1 -d' '`
declare -ax othernodes=`echo ${nodes[@]} | sed s/${masternode}//`
export size=${#nodes[@]}
export VERSION='3.1.1'

for node in ${othernodes} 
do
    curl --noproxy ${masternode} -XPOST "http://${COUCH_USER}:${COUCH_PASSWORD}@${masternode}:5984/_cluster_setup" \
      --header "Content-Type: application/json"\
      --data "{\"action\": \"enable_cluster\", \"bind_address\":\"0.0.0.0\",\
             \"username\": \"${COUCH_USER}\", \"password\":\"${COUCH_PASSWORD}\", \"port\": \"5984\",\
             \"remote_node\": \"${node}\", \"node_count\": \"$(echo ${nodes[@]} | wc -w)\",\
             \"remote_current_user\":\"${COUCH_USER}\", \"remote_current_password\":\"${COUCH_PASSWORD}\"}"
done

for node in ${othernodes}
do
    curl --noproxy ${masternode} -XPOST "http://${COUCH_USER}:${COUCH_PASSWORD}@${masternode}:5984/_cluster_setup"\
      --header "Content-Type: application/json"\
      --data "{\"action\": \"add_node\", \"host\":\"${node}\",\
             \"port\": \"5984\", \"username\": \"${COUCH_USER}\", \"password\":\"${COUCH_PASSWORD}\"}"
done

curl --noproxy ${masternode} -XGET "http://${COUCH_USER}:${COUCH_PASSWORD}@${masternode}:5984/"

curl --noproxy ${masternode} -XPOST "http://${COUCH_USER}:${COUCH_PASSWORD}@${masternode}:5984/_cluster_setup"\
    --header "Content-Type: application/json" --data "{\"action\": \"finish_cluster\"}"

for node in "${nodes[@]}"; do  curl --noproxy ${node} -X GET "http://${COUCH_USER}:${COUCH_PASSWORD}@${node}:5984/_membership"; done