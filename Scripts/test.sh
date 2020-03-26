#!/bin/bash

IP_ADDR="172.20.0."
NETWORK_NAME="pumba_net"
# must be even number of clients for sake of simplicity
TOTAL_SUBSCRIBERS=2
NR_SUBSCRIBERS_PER_BROKER=2
NR_BROKERS=$((TOTAL_SUBSCRIBERS/NR_SUBSCRIBERS_PER_BROKER))


PWD=$(pwd)
FIST_BROKER_NUM=2
LAST_BROKER_NUM=$((NR_BROKERS+1))

broker=5
sub=1
pub=1

docker run -d --rm -it --network=$NETWORK_NAME \
			--ip="$IP_ADDR$broker$pub" \
			--name="pub_$broker$pub" \
			piersfinlayson/mosquitto-clients mosquitto_pub \
			-h "$IP_ADDR$broker"  \
			-t test  \
			-m "$IP_ADDR$broker$pub - $(date +'%Y-%m-%d %T.%3N')" \
			-d | xargs -d$'\n' -L1 bash -c 'date "+%Y-%m-%d %T.%3N -> $0"'

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


