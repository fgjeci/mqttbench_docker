#!/bin/bash

echo "Cleaning the environment..."
docker stop $(docker ps -a -q)
docker rm $(docker ps -a -q)

docker network rm pumba_net

echo "Creating a new network..."
docker network create \
		--driver=bridge \
		--subnet=172.20.0.0/16 \
		--ip-range=172.20.0.0/24 \
		pumba_net

echo "Creating brokers..."
echo -e "type EMQX"
#docker run -d --network=pumba_net\
#		--hostname emqx1 --name b1 \
#		-p 1883:1883 \
#		-e EMQX_NAME="emqx1" \
#        -e EMQX_NODE__DIST_LISTEN_MAX=6379 \
#        -e EMQX_LISTENER__TCP__EXTERNAL=1883 \
#        -e EMQX_CLUSTER__DISCOVERY="static" \
#        -e EMQX_CLUSTER__STATIC__SEEDS="emqx2@172.20.0.3" \
#		flipperthedog/emqx-pumba
#
#docker run -d --network=pumba_net\
#		--hostname emqx2 --name b2 \
#		-p 1884:1883 \
#		-e EMQX_NAME="emqx2" \
#        -e EMQX_NODE__DIST_LISTEN_MAX=6379 \
#        -e EMQX_LISTENER__TCP__EXTERNAL=1883 \
#        -e EMQX_CLUSTER__DISCOVERY="static" \
#        -e EMQX_CLUSTER__STATIC__SEEDS="emqx1@172.20.0.2" \
#		flipperthedog/emqx-pumba
#

function MULTI_HOST {
  current_bkr=$1

  for i in $(seq 1 5)
    do
      docker exec -it b1 sh -c "echo '172.20.0.$((i+2))      rabbit$i' >> /etc/hosts"
      echo "cluster_formation.classic_config.nodes.$i = docker@rabbit$i" >>  ~/confiles/rabbit_"$current_bkr".conf
    done
}


 docker run -d --network=pumba_net \
 		--hostname rabbit1 --name b1 \
 		-p 5672:5672 \
 		-v ~/confiles/rabbitmq1.conf:/etc/rabbitmq/rabbitmq.conf \
 		-e RABBITMQ_ERLANG_COOKIE=$(cat ~/.erlang.cookie) \
 		-e RABBITMQ_NODENAME=docker@rabbit1 \
 		flipperthedog/rabbitmq:ping

  $(MULTI_HOST 1)
 #can be added directly in the run with add-hosts though
 #docker exec -it b1 sh -c "echo '172.20.0.3      rabbit2' >> /etc/hosts"


 docker run -d --network=pumba_net \
 		--hostname rabbit2 --name b2 \
 		-p 5673:5672 \
 		-v ~/confiles/rabbitmq2.conf:/etc/rabbitmq/rabbitmq.conf \
 		--add-host=rabbit1:172.20.0.2 \
 		-e RABBITMQ_ERLANG_COOKIE=$(cat ~/.erlang.cookie) \
 		-e RABBITMQ_NODENAME=docker@rabbit2 \
 		flipperthedog/rabbitmq:ping

 #docker exec -it b2 sh -c "echo '172.20.0.2      rabbit1' >> /etc/hosts"

#echo "Slowing down the network..."
#sleep 20
#
#docker run -d --rm --network=pumba_net \
# 		--name pumba \
#		-v /var/run/docker.sock:/var/run/docker.sock gaiaadm/pumba netem \
#		--interface eth0 \
#		--duration 15m \
#		delay --time 50 \
#		b1 b2

# publish
# docker run --rm -ti --network=pumba_net piersfinlayson/mosquitto-clients mosquitto_pub -h 172.20.0.3  -t test -m $(gdate +"%Y-%m-%d_%T.%3N") -d | xargs -d$'\n' -L1 bash -c 'gdate "+%Y-%m-%d %T.%3N ---- $0"'
# subscribe 
# docker run --rm -ti --network=pumba_net piersfinlayson/mosquitto-clients mosquitto_sub -h 172.20.0.2  -t test  -d | xargs -d$'\n' -L1 bash -c 'gdate "+%Y-%m-%d %T.%3N ---- $0"'