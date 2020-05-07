#!/bin/bash

IP_ADDR=172.20.0.
NETWORK_NAME=pumba_net
# must be even number of clients for sake of simplicity
TOTAL_SUBSCRIBERS=2
NR_SUBSCRIBERS_PER_BROKER=2
NR_BROKERS=$((TOTAL_SUBSCRIBERS/NR_SUBSCRIBERS_PER_BROKER))
DURATION_SIM=15m


PWD=$(pwd)
FIST_BROKER_NUM=2
LAST_BROKER_NUM=$((NR_BROKERS+1))

broker=5
sub=1
pub=1

DEFAULT_INTERFACE='eth0'
NETWORK_DRIVER=bridge

###### MAIN ######
echo "Cleaning up the environment..."
docker stop $(docker ps -a -q)
docker rm $(docker ps -a -q)

docker network rm "$NETWORK_NAME"

echo "Creating a new network..."
docker network create --driver="$NETWORK_DRIVER" \
		--subnet="$IP_ADDR"0/16 \
		"$NETWORK_NAME"


docker run -d -it --rm --network="$NETWORK_NAME" \
                --hostname vernemq2 \
		--name d2 \
		--ip='172.20.0.2' \
		-e 'DOCKER_VERNEMQ_NODENAME=172.20.0.2' \
                francigjeci/vernemq-debian:latest

#
docker run -d -it --rm --network="$NETWORK_NAME" \
                --hostname vernemq3 \
		--name d3 \
		--ip='172.20.0.3' \
		-e 'DOCKER_VERNEMQ_NODENAME=172.20.0.3' \
		-e 'DOCKER_VERNEMQ_DISCOVERY_NODE=172.20.0.2' \
                francigjeci/vernemq-debian:latest

echo "The docker created"
dockers_name=$(docker ps --format "{{.Names}}" | tr '\r\n' ' ')
echo $dockers_name

sleep 10

#docker run -it --rm --network=pumba_net \
#		--name=pumba \
#		-v /var/run/docker.sock:/var/run/docker.sock gaiaadm/pumba \
#		pumba netem --duration 15m \
#		d2 d3

#docker run -d --network=pumba_net \
#		-v /var/run/docker.sock:/var/run/docker.sock gaiaadm/pumba netem \
#		$(docker ps --format "{{.Names}}"  | tr '\r\n' ' ')

#delay --time 50 \
#--interface eth0 \
#--duration 15m \

#docker run -d --rm -it --network=$NETWORK_NAME \
#			--ip="$IP_ADDR$broker$pub" \
#			--name="pub_$broker$pub" \
#			piersfinlayson/mosquitto-clients mosquitto_pub \
#			-h "$IP_ADDR$broker"  \
#			-t test  \
#			-m "$IP_ADDR$broker$pub - $(date +'%Y-%m-%d %T.%3N')" \
#			-d | xargs -d$'\n' -L1 bash -c 'date "+%Y-%m-%d %T.%3N -> $0"'

#echo "Subscriber $IP_ADDR$broker$sub subscribing to broker $IP_ADDR$broker"
#docker run --rm -ti --network=$NETWORK_NAME \
#		--ip="$IP_ADDR$broker$sub" \
#		--name="sub_$broker$sub" \
#		piersfinlayson/mosquitto-clients mosquitto_sub \
#		-h "$IP_ADDR$broker"  \
#		-t test  \
#		-d | xargs -d$'\n' -L1 bash -c 'date "+%Y-%m-%d %T.%3N ---- $0"' \
#		| xargs -d$'\n' -L1 echo "$IP_ADDR$broker$sub -" >> "../Network Analysis/log$broker$sub.log"



# echo $'received' | xargs -d$'\n' -L1  bash -c $'date "+%Y-%m-%d %T.%3N ---- $0"' | xargs -d$'\n' -L1  bash -c '(hostname -I ; echo $" $COLUMNS $0") | tr -d "\n"'
# echo $'received' | xargs -d$'\n' -L1  bash -c $'date "+%Y-%m-%d %T.%3N ---- $0"' | xargs -d$'\n' -L1  bash -c '(/sbin/ifconfig eth0 | grep "inet addr:"| cut -d: -f2 | awk "{print $1}" ; echo " $COLUMNS $0") | tr -d "\n"'


# /sbin/ifconfig eth0 | grep 'inet addr:'| cut -d: -f2 | awk '{print $1}'


