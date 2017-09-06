# https://www.digitalocean.com/community/tutorials/how-to-set-up-a-private-docker-registry-on-ubuntu-1
openssl genrsa -out devdockerCA.key 2048
openssl req -x509 -new -nodes -key devdockerCA.key -days 10000 -out devdockerCA.crt
openssl genrsa -out cpascal.key 2048
# IMPORTANT!: For example, if your Docker registry is going to be running on the domain www.ilovedocker.com, then your input should look like this:
openssl req -new -key cpascal.key -out cpascal.csr
openssl x509 -req -in cpascal.csr -CA devdockerCA.crt -CAkey devdockerCA.key -CAcreateserial -out cpascal.crt -days 10000
