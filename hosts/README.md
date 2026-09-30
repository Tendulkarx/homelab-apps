# Which host runs which folder

One file per host, one folder per line. Each host checks out only its own folders (git sparse
checkout), so `/opt/docker` there, and Arcane on prdsrv1, show only what that host runs. Files
at the top of the repo are always there; every list also names `hosts`, so this folder is too.

After changing a list, on that host:

```bash
cd /opt/docker && git pull && git sparse-checkout set $(cat hosts/$(hostname -s))
```

Moving an app to another host: add its folder to the new host's list first, move it (stop,
copy `data/` and `.env`, start), then remove it from the old host's list. Sparse checkout
never deletes files git does not track (`data/`, `.env`), so the old copy stays until removed
by hand.
