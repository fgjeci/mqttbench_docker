ARG BASEIMAGE=python:3.8.2-slim

# Starting from the base image we build the new image containing the python file
FROM ${BASEIMAGE}

# ensure local python is preferred over distribution python
ENV PATH /usr/local/bin:$PATH

# Update and install numpy & paho-mqtt
RUN apt-get update \
	&& pip install numpy \
	&& pip install paho-mqtt


WORKDIR /home

CMD ["bash"]

# CMD ["python3"]

# CMD ["python3", "-u" ,"script.py"]
