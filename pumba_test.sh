#!/bin/bash

docker stop $(docker ps -a -q)
docker rm $(docker ps -a -q)

docker network create -d bridge pumba_net

docker run -d --network=pumba_net \
		--hostname rabbit1 --name d1 \
		-p 5672:5672 \
		-v ~/confiles/rabbitmq1.conf:/etc/rabbitmq/rabbitmq.conf \
		-e RABBITMQ_ERLANG_COOKIE=$(cat ~/.erlang.cookie) \
		-e RABBITMQ_NODENAME=docker@rabbit1 \
		flipperthedog/rabbitmq:ping

#can be added directly in the run with add-hosts though
docker exec -it d1 sh -c "echo '172.19.0.3      rabbit2' >> /etc/hosts" 


docker run -d --network=pumba_net \
		--hostname rabbit2 --name d2 \
		-p 5673:5672 \
		-v ~/confiles/rabbitmq2.conf:/etc/rabbitmq/rabbitmq.conf \
		-e RABBITMQ_ERLANG_COOKIE=$(cat ~/.erlang.cookie) \
		-e RABBITMQ_NODENAME=docker@rabbit2 \
		flipperthedog/rabbitmq:ping

docker exec -it d2 sh -c "echo '172.19.0.2      rabbit1' >> /etc/hosts"

sleep 20
echo "slowing down the network"

docker run -d --rm --network=pumba_net \
		-v /var/run/docker.sock:/var/run/docker.sock gaiaadm/pumba netem \
		--interface eth0 \
		--duration 15m \
		delay --time 1000 \
		d1 d2
