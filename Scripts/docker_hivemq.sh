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
# --ip 172.20.0.2 \
# --entrypoint /opt/hivemq/bin/run.sh \
#--gateway=172.20.0.254 \
#--subnet=172.20.0.0/16 \
#--ip-range=172.20.0.0/24 \

############### Create the config file##################

config_template_file=../config/config-dns.xml
output_file=../config/config-dns_1.xml

ip_pool=172.22.0
port_disc_node=8000


sudo cp $config_template_file $output_file
sudo xmlstarlet ed -L -s '//discovery/static' -t elem -n 'node' $output_file 
sudo xmlstarlet ed -L -s "//discovery/static/node[last()]" -t elem -n 'host' -v $ip_pool.3 $output_file
sudo xmlstarlet ed -L -s "//discovery/static/node[last()]" -t elem -n 'port' -v $port_disc_node $output_file
sudo xmlstarlet ed -L -s '//discovery/static' -t elem -n 'node' $output_file 
sudo xmlstarlet ed -L -s "//discovery/static/node[last()]" -t elem -n 'host' -v $ip_pool.4 $output_file
sudo xmlstarlet ed -L -s "//discovery/static/node[last()]" -t elem -n 'port' -v $port_disc_node $output_file


docker stop $(docker ps -a -q)
docker rm $(docker ps -a -q)
# Remove the older network
docker network rm pumba_hivemq

docker network create --driver=bridge \
			--subnet=$ip_pool.0/24 \
			pumba_hivemq

docker run -d --network=pumba_hivemq \
		--hostname hivemq1 \
		--name d1 \
		--ip=$ip_pool.2 \
		-p 5674:5674 \
		-v $output_file:/opt/hivemq/conf/config.xml \
		-e HIVEMQ_BIND_ADDRESS=$ip_pool.2 \
		hivemq/hivemq:dns-image

#sleep 4 
# -p 5674:5674 \
#can be added directly in the run with add-hosts though
# --entrypoint /opt/hivemq/bin/run.sh \
# docker exec -it --user root d1 sh -c "/opt/hivemq/bin/run.sh" &
#--ip 172.20.0.3 \

docker run -d --network=pumba_hivemq \
		--hostname hivemq2 \
		--name d2 \
		--ip=$ip_pool.3 \
		-p 5675:5674 \
		-v /home/franci/Documents/Docker_Files/config/config-dns_2.xml:/opt/hivemq/conf/config.xml \
		-e HIVEMQ_BIND_ADDRESS=$ip_pool.3 \
		hivemq/hivemq:dns-image
#can be added directly in the run with add-hosts though
# /usr/sbin/
# -p 5675:5674 \
#docker exec -it --user root d2 sh -c "/opt/hivemq/bin/run.sh" &


docker run -d --network=pumba_hivemq \
		--hostname hivemq3 \
		--name d3 \
		--ip=$ip_pool.4 \
		-p 5676:5674 \
		-v /home/franci/Documents/Docker_Files/config/config-dns_3.xml:/opt/hivemq/conf/config.xml \
		-e HIVEMQ_BIND_ADDRESS=$ip_pool.4 \
		hivemq/hivemq:dns-image


sleep 10
echo "slowing down the network"

docker run -d --rm --network=pumba_hivemq \
                -v /var/run/docker.sock:/var/run/docker.sock gaiaadm/pumba netem \
                --interface eth0 \
		--duration 15m \
                delay --time 1000 \
                d1 d2


#--duration 15m \
