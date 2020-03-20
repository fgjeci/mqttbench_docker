#!/bin/bash

config_template_file=../config/config-dns.xml
output_file=../config/config-dns_new_1.xml

ip_pool=172.22.0
port_disc_node=8000

PWD=$(pwd)

function CREATE_HIVEMQ_CONFIG {
	config_template_file=$1
	output_file=$2

	ip_pool=$IP_ADDR
	port_disc_node=8000
	# Copy the template file to new file
	sudo cp $config_template_file $output_file
	# Delete all nodes present in the static tag
	# Necessary to avoid wrong parsing during adding new node elements 
	sudo xmlstarlet ed -L -d '//discovery/static/node' $output_file
	# Adding node elements
	for i in $(seq $FIST_BROKER_NUM $LAST_BROKER_NUM)
	    do
		
		# First we add the host and port of the actual node
		sudo xmlstarlet ed -L -s '//discovery/static' -t elem -n 'node' $output_file 
		sudo xmlstarlet ed -L -s "//discovery/static/node[last()]" -t elem -n 'host' -v $ip_pool{$i} $output_file
		sudo xmlstarlet ed -L -s "//discovery/static/node[last()]" -t elem -n 'port' -v $port_disc_node $output_file

	    done
}



