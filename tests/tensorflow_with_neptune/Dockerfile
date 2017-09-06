FROM gcr.io/tensorflow/tensorflow:latest-gpu
RUN apt-get -y update
RUN apt-get install -y python3-pip python-pip iputils-ping
RUN pip install neptune-cli==1.6.3
RUN pip install keras
RUN mkdir -p /mnt/mhome
