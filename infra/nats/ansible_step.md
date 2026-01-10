# Ansible Step to Set Up NATS Server for Improv Show

1) Make the directory `/opt/show/nats/pki` on the NATS server machine and set its permissions to `700` and ownership to the appropriate user.
2) Copy the `server_for_show.conf` file from the Ansible control machine to `/opt/show/nats/server.conf` on the NATS server machine, ensuring the file permissions are set to `600`.
3) Copy the NATS server TLS certificate and key files from the Ansible control machine to `/opt/show/nats/pki/` on the NATS server machine, ensuring the file permissions are set to `600`.
4) Pull the latest NATS server Docker image on the NATS server machine.
5) Run the NATS server Docker container with the following specifications:
   - Name the container `improv-nats-server`.
   - Use the `nats:latest` image.
   - Mount the host directory `/opt/show/nats` to `/persistent` in the container.
   - Set the container to always restart unless stopped manually.
   - Run the container in detached mode.
   - Use the command to start the NATS server with the configuration file located at `/persistent/server.conf`.
6) Ensure the NATS server is running and accessible on the specified host and port.

## Local NATS Client Setup for Testing

1) Deploy nats server locally.

  ```sh
  docker pull nats:latest
  docker run --rm \
    --mount type=bind,source=/opt/show/nats,target=/persistent \
    -p 127.0.0.1:4222:4222 \
    -p 127.0.0.1:8222:8222 \
    -ti \
    nats:latest \
    -c /persistent/server.conf
  ```

2) Use the NATS CLI to connect to the local NATS server for testing.

  ```sh
  nats \
  --server tls://127.0.0.1:4222 \
  --tlsca ./secrets/pki/intermediateCA/certs/ca-chain.cert.pem \
  --tlscert  ./secrets/pki/intermediateCA/certs/admin.client.cert.pem \
  --tlskey  ./secrets/pki/intermediateCA/private/admin.client.key.pem  \
  server info
  ```
