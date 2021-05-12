# This should be run via ssh onto one of the compute instances

set -euxo pipefail

# This is based on Docker's assignment of static IP addresses depending on the order containers are started in
# so for these addresses to work, there need to be no other containers running when this script is run.
# As an added measure though, we also specify the ip address when creating the container.
declare -ax nodes=(172.17.0.4 172.17.0.3 172.17.0.2)
export masternode=`echo ${nodes} | cut -f1 -d' '`
declare -ax othernodes=`echo ${nodes[@]} | sed s/${masternode}//`
export size=${#nodes[@]}
export user='admin'
export pass='answering_railcar'
export VERSION='3.1.1'
export cookie='a192aeb9904e6590849337933b000c99'

# Give the nodes some time to start up
sleep 10

for node in ${othernodes} 
do
    curl --noproxy ${masternode} -XPOST "http://${user}:${pass}@${masternode}:5984/_cluster_setup" \
      --header "Content-Type: application/json"\
      --data "{\"action\": \"enable_cluster\", \"bind_address\":\"0.0.0.0\",\
             \"username\": \"${user}\", \"password\":\"${pass}\", \"port\": \"5984\",\
             \"remote_node\": \"${node}\", \"node_count\": \"$(echo ${nodes[@]} | wc -w)\",\
             \"remote_current_user\":\"${user}\", \"remote_current_password\":\"${pass}\"}"
done

for node in ${othernodes}
do
    curl --noproxy ${masternode} -XPOST "http://${user}:${pass}@${masternode}:5984/_cluster_setup"\
      --header "Content-Type: application/json"\
      --data "{\"action\": \"add_node\", \"host\":\"${node}\",\
             \"port\": \"5984\", \"username\": \"${user}\", \"password\":\"${pass}\"}"
done

curl --noproxy ${masternode} -XGET "http://${user}:${pass}@${masternode}:5984/"

curl --noproxy ${masternode} -XPOST "http://${user}:${pass}@${masternode}:5984/_cluster_setup"\
    --header "Content-Type: application/json" --data "{\"action\": \"finish_cluster\"}"

for node in "${nodes[@]}"; do  curl --noproxy ${node} -X GET "http://${user}:${pass}@${node}:5984/_membership"; done