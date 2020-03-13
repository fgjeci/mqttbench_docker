# MQTTbench Docker

## EQMX
- Source: 
  + based on: [3.2 Alpine](https://github.com/emqx/emqx-docker/blob/master/v3.2/Dockerfile)
  + final image: [custom img](https://hub.docker.com/r/flipperthedog/emqx-bash)

- Adaptation done:
  + add the following packages to the Dockerfile (via `apk add`):
    - iputils
    - iproute2
    - net-tools
    - iperf
    - busybox-extras
    - xterm (_not working_)
    - bash (_not working_)
  + change the user to **root**: `USER root`
  + install bash from the inside: `apk add --no-cache bash` 

## RABBITMQ
- Source: 
  + based on: [3.8 Ubuntu](https://github.com/docker-library/rabbitmq/blob/853ba639f40baeb1f6ae021730fe8b71386b0999/3.8/ubuntu/Dockerfile)
  + final image: [custom img](https://hub.docker.com/r/flipperthedog/rabbitmq)
  
- Adaptation done:
  + add the following packages to the Dockerfile (via `apt-get`):
    - net-tools
    - iputils-ping
    - iproute2


## VerneMQ
- Source: 
  + based on: 
    - [Debian](https://github.com/vernemq/docker-vernemq/blob/master/Dockerfile)
  + final image: [custom img](https://hub.docker.com/r/francigjeci/vernemq-debian)

- Adaptation done:
  + add the following packages to the Dockerfile (via `apk add`):
    - iputils
    - iproute2
    - net-tools
  + change the user to **root**: `USER root`
  #### In the Debian distribution, parameters can be passed through environmental parameters 
  + Accept the license terms: 
    - `"DOCKER_VERNEMQ_ACCEPT_EULA": "yes"` -  env parameter
  + Allow anonymous communication: 
    - `"DOCKER_VERNEMQ_ALLOW_ANONYMOUS":"on"`
  #### Alternitavely, these enviroment parameters can be preconfigured in the docker file 
  + Accept the license terms: 
    - `ENV DOCKER_VERNEMQ_ACCEPT_EULA=yes`
  + Allow anonymous communication: 
    - `DOCKER_VERNEMQ_ALLOW_ANONYMOUS=on`
  
- Source: 
  + based on: 
    - [3.9 Alpine](https://github.com/vernemq/docker-vernemq/blob/master/Dockerfile.alpine)
  + final image: [custom img]()

- Adaptation done:
  + add the following packages to the Dockerfile (via `apk add`):
    - iputils
    - iproute2
    - net-tools
    - iperf
    - xterm
    - busybox-extras
  + change the user to **root**: `USER root`
  #### In the Alpine distribution, parameters should be changed by means of command line commands
  + Accept the license terms:
        
        'echo "accept_eula = yes" >> /vernemq/etc/vernemq.conf'
  
  + Change the nodename of the MQTT docker 
  
        `sed -i "/nodename = VerneMQ@127.0.0.1/s/= .*/= dev1@172.17.0.2/" /vernemq/etc/vernemq.conf`
        'sed -i "/VerneMQ@127.0.0.1/s/ .*/ dev2@172.17.0.3/" /vernemq/etc/vm.args'

  
  
  

## HiveMQ
- Source: 
<<<<<<< HEAD
  + based on: [4.2 HiveMQ](https://github.com/hivemq/hivemq4-docker-images/tree/master/hivemq4/dns-image/Dockerfile)  
  + final image: [custom img]()

=======
  + based on: [3.8 Ubuntu](https://github.com/docker-library/rabbitmq/blob/853ba639f40baeb1f6ae021730fe8b71386b0999/3.8/ubuntu/Dockerfile)
  + final image: [custom img](https://hub.docker.com/r/flipperthedog/rabbitmq)
  
>>>>>>> 25dd2660bfb91c60433bab44e107add6f1a0ed1d
- Adaptation done:
  + add the following packages to the Dockerfile (via `apt-get`):
    - net-tools
    - iputils-ping
    - iproute2

- DNS discovery image
  + The image has been configured with the discovery extension. 
  This permits the creation of broker clusters.
