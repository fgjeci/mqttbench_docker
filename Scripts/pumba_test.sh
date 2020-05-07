#!/bin/bash

echo $(docker ps --format "{{.Names}}" | tr '\r\n' ' ')

docker run -d -it --rm -v /var/run/docker.sock:/var/run/docker.sock gaiaadm/pumba:0.7.2 \
netem --duration 15m delay --time 50 d2 d3

#--network='pumba_net' --ip='172.20.0.10' \
#--duration 15m d2


#docker run --rm --network=pumba_net \
#		--name=pumba \
#		-v /var/run/docker.sock:/var/run/docker.sock gaiaadm/pumba:0.7.2 \
#		pumba netem --duration 15m \
#		d2 d3
