#!/bin/bash

docker stop $(docker ps -a -q)
docker rm $(docker ps -a -q)

# --gateway=172.20.0.254 \
# --subnet=172.20.0.0/24 \
# --ip-range=172.20.0.0/24 \
# -p 5684:5684 \
# -e DOCKER_VERNEMQ_ACCEPT_EULA=yes \
# -e DOCKER_VERNEMQ_ALLOW_ANONYMOUS=on \

# --subnet is crucial to set a static ip address to the docker so that one can configure the cluster properties

docker network create --driver bridge \
			--subnet 172.20.0.0/24 \
			pumba_vernemq

# -e 'DOCKER_IP_ADDRESS=172.20.0.2' \

docker run -d --network pumba_vernemq \
		--hostname vernemq1 \
		--name d1 \
		--ip=172.20.0.2 \
		-e 'DOCKER_VERNEMQ_NODENAME=172.20.0.2' \
		vernemq/vernemq:debian


# docker exec -d -it --user root d1 sh -c "/usr/sbin/start_vernemq.sh" &
# --ip 172.20.0.3 \
# -p 5685:5684 \

# -e 'DOCKER_IP_ADDRESS=172.20.0.3' \
# -e 'DOCKER_VERNEMQ_DISCOVERY_NODE=172.20.0.2' \

docker run -d --network=pumba_vernemq \
                --hostname vernemq2 \
		--name d2 \
		--ip=172.20.0.3 \
		-e 'DOCKER_VERNEMQ_NODENAME=172.20.0.3' \
		-e 'DOCKER_VERNEMQ_DISCOVERY_NODE=172.20.0.2' \
                vernemq/vernemq:debian



# -e 'DOCKER_VERNEMQ_DISCOVERY_NODE=172.20.0.2, 172.20.0.3'

docker run -d --network=pumba_vernemq \
                --hostname vernemq3 \
		--name d3 \
		--ip=172.20.0.4 \
		-e 'DOCKER_VERNEMQ_NODENAME=172.20.0.4' \
		-e 'DOCKER_VERNEMQ_DISCOVERY_NODE=172.20.0.2' \
                vernemq/vernemq:debian

sleep 10
echo "slowing down the network"

docker run -d --network=pumba_vernemq \
                -v /var/run/docker.sock:/var/run/docker.sock gaiaadm/pumba netem \
                --interface eth0 \
		--duration 15m \
                delay --time 50 \
                d1 d2

docker run -d --network=pumba_vernemq \
                -v /var/run/docker.sock:/var/run/docker.sock gaiaadm/pumba netem \
                --interface eth0 \
		--duration 15m \
                delay --time 50 \
                d2 d3

docker run -d --network=pumba_vernemq \
                -v /var/run/docker.sock:/var/run/docker.sock gaiaadm/pumba netem \
                --interface eth0 \
		--duration 15m \
                delay --time 50 \
                d1 d3



# Joining the cluster
# docker exec -d -it --user root d2 sh -c "vmq-admin cluster join discovery-node=VerneMQ@172.20.0.1" &

# docker exec -d -it --user root d3 sh -c "vmq-admin cluster join discovery-node=VerneMQ@172.20.0.1" &


# --entrypoint /vernemq/bin/vernemq start \
# -p 5685:5684 \
#can be added directly in the run with add-hosts though
# /usr/sbin/

#-p 5684:5684 \
# -e DOCKER_VERNEMQ_NODENAME=172.22.0.2 \
# -e DOCKER_VERNEMQ_DISCOVERY_NODE=172.22.0.3 \

#sleep 4
#can be added directly in the run with add-hosts though
# /usr/sbin/

#--duration 15m \

#-e DOCKER_VERNEMQ_ALLOW_ANONYMOUS=on \
#-e DOCKER_VERNEMQ_DISCOVERY_NODE=docker2@vernemq \
#-e DOCKER_VERNEMQ_NODENAME=docker1@vernemq \
#-e DOCKER_VERNEMQ_ACCEPT_EULA=yes \
#HiveMQ
#/opt/hivemq/bin/run.sh
#--entrypoint /usr/sbin/start_vernemq \
#5674:5674
# tail -f /dev/null -> Tail at the end of the command is used to keep running the container, since running a container in the background, -d (dettached mode), will make
# the container to stop after a while, becuase it things the service is closed and it will stop
#-e HIVEMQ_BIND_ADDRESS=10.0.0.251 \
