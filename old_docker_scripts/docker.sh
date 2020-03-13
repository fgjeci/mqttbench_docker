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

docker stop $(docker ps -a -q)
docker rm $(docker ps -a -q)

docker network create -d bridge pumba_fra_test

docker run -d --network=pumba_fra_test \
		--hostname vernemq1 --name d1 \
		--entrypoint /opt/hivemq/bin/run.sh \
		-v /home/franci/Documents/Docker_Files/Python/config-dns_1.xml:/opt/hivemq/conf/config.xml \
		-p 5674:5674 \
		-e HIVEMQ_BIND_ADDRESS='10.0.0.251' \
		hivemq/hivemq4:dns-image

sleep 4


#can be added directly in the run with add-hosts though
# /usr/sbin/
#docker exec -d -it --user root d1 sh -c "/opt/hivemq/bin/run.sh"

docker run -d --network=pumba_fra_test \
		--hostname vernemq2 --name d2 \
		-v /home/franci/Documents/Docker_Files/Python/config-dns_2.xml:/opt/hivemq/conf/config.xml \
		--entrypoint /opt/hivemq/bin/run.sh \
		-p 5675:5674 \
		-e HIVEMQ_BIND_ADDRESS='10.0.0.252' \
		hivemq/hivemq4:dns-image \
		tail -f /dev/null


#can be added directly in the run with add-hosts though
# /usr/sbin/
#docker exec -d -it --user root d2 sh -c "/opt/hivemq/bin/run.sh"

sleep 20
echo "slowing down the network"

docker run -d --rm --network=pumba_fra_test \
		-v /var/run/docker.sock:/var/run/docker.sock gaiaadm/pumba netem \
		--interface eth0 \
		--duration 15m \
		delay --time 1000 \
		d1 d2



