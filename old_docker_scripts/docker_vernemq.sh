#!/bin/bash
#-e DOCKER_VERNEMQ_ALLOW_ANONYMOUS=on \
#-e DOCKER_VERNEMQ_DISCOVERY_NODE=docker2@vernemq \
#-e DOCKER_VERNEMQ_NODENAME=docker1@vernemq \
#-e DOCKER_VERNEMQ_ACCEPT_EULA=yes \
#HiveMQ
#/opt/hivemq/bin/run.sh
#/usr/sbin/start_vernemq
#5674:5674
# tail -f /dev/null -> Tail at the end of the command is used to keep running the container, since running a container in the background, -d (dettached mode), will make
# the container to stop after a while, becuase it things the service is closed and it will stop
#-e HIVEMQ_BIND_ADDRESS=10.0.0.251 \


docker stop $(docker ps -a -q)
docker rm $(docker ps -a -q)
docker network rm pumba_vernemq

docker network create -d bridge --subnet=172.22.0.0/16 \
                --ip-range=172.22.0.0/24 \
                pumba_vernemq

docker run -d --network=pumba_vernemq \
		--hostname vernemq1 --name d1 \
		-p 5684:5684 \
		-e DOCKER_VERNEMQ_ACCEPT_EULA=yes \
		-e DOCKER_VERNEMQ_ALLOW_ANONYMOUS=on \
		-e DOCKER_VERNEMQ_NODENAME=172.22.0.2 \
		-e DOCKER_VERNEMQ_DISCOVERY_NODE="172.22.0.3, 172.22.0.4" \
                flipperthedog/vernemq:latest

docker run -d --network=pumba_vernemq \
                --hostname vernemq2 --name d2 \
                -p 5685:5684 \
                -e DOCKER_VERNEMQ_ACCEPT_EULA=yes \
                -e DOCKER_VERNEMQ_ALLOW_ANONYMOUS=on \
                -e DOCKER_VERNEMQ_NODENAME=172.22.0.3 \
                -e DOCKER_VERNEMQ_DISCOVERY_NODE="172.22.0.2, 172.22.0.4" \
                flipperthedog/vernemq:latest

docker run -d --network=pumba_vernemq \
                --hostname vernemq3 --name d3 \
                -p 5686:5684 \
                -e DOCKER_VERNEMQ_ACCEPT_EULA=yes \
                -e DOCKER_VERNEMQ_ALLOW_ANONYMOUS=on \
                -e DOCKER_VERNEMQ_NODENAME=172.22.0.4 \
                -e DOCKER_VERNEMQ_DISCOVERY_NODE="172.22.0.2, 172.22.0.3" \
                flipperthedog/vernemq:latest

#####
#VERNEMQ COMMANDS
#execute commands: vmq-admin
#show cluster status: vmq-admin cluster show
#vmq-admin cluster join discovery-node=VerneMQ@172.20.0.5