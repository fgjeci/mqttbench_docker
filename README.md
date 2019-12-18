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
