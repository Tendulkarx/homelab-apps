# dozzle-agent

Dozzle on prdsrv1 reads prdsrv2's and prdsrv3's logs through this agent (port 7007). Agent and
Dozzle authenticate each other with one certificate made for this lab; Dozzle's built-in one is
the same in every install, so it would let any Dozzle on the network read these logs and run
commands in these containers.

The certificate is not in git (`*/data/`). To make a new one (all three hosts at once):

```bash
docker run --rm -v "$PWD":/out amir20/dozzle:v11.1.2 generate-certs \
  --cert-out /out/cert.pem --key-out /out/key.pem
```

then copy both files to `dozzle/data/` on prdsrv1 and `dozzle-agent/data/` on prdsrv2 and
prdsrv3 (mode 600 for the key), and `docker compose up -d --force-recreate` in each.
