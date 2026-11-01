# SSH tunnel setup (BaxAuto)

Use this when the database listens on a remote host’s loopback (`127.0.0.1`) or a private network, and BaxAuto reaches it through an SSH bastion / jump host.

BaxAuto opens an **SSH local port forward**, then talks to Postgres/MySQL/… on `127.0.0.1:<ephemeral-port>` inside the API process.

---

## What you need

| Piece | Where it lives |
|--------|----------------|
| SSH host (bastion) | Machine BaxAuto can reach on port 22 (or your SSH port) |
| SSH user | Account on the bastion that can open tunnels |
| Auth | Private key (preferred) **or** password |
| Host key fingerprint | SHA256 fingerprint of the **bastion’s host key** |
| DB host/port in the form | Usually `127.0.0.1` and the engine port **as seen from the bastion** |

---

## 1. Create an SSH user on the bastion (optional)

On the **destination / bastion** host:

```bash
sudo adduser --disabled-password baxauto
sudo mkdir -p /home/baxauto/.ssh
sudo chmod 700 /home/baxauto/.ssh
```

Prefer key auth with no login password for the tunnel user.

---

## 2. Generate a key pair (on your laptop or the BaxAuto host)

```bash
ssh-keygen -t ed25519 -f ~/.ssh/baxauto_tunnel -N ""
```

- **Private key** (`baxauto_tunnel`) → paste into BaxAuto connection → SSH private key  
- **Public key** (`baxauto_tunnel.pub`) → one line in the bastion’s `authorized_keys`

---

## 3. Install the public key on the bastion

Copy the **public** key to the **same machine** you set as SSH host in BaxAuto (easy to put it on the wrong box).

```bash
# On the bastion, as root or with sudo:
sudo tee -a /home/baxauto/.ssh/authorized_keys < /path/to/baxauto_tunnel.pub
sudo chown -R baxauto:baxauto /home/baxauto/.ssh
sudo chmod 600 /home/baxauto/.ssh/authorized_keys
```

Verify from a machine that can reach the bastion:

```bash
ssh -i ~/.ssh/baxauto_tunnel baxauto@BASTION_IP
# Non-default SSH port (example: 2222):
ssh -p 2222 -i ~/.ssh/baxauto_tunnel baxauto@BASTION_IP
```

If you get `Permission denied (publickey)`:

1. Confirm you edited `authorized_keys` on **BASTION_IP**, not another server.  
2. Confirm the `.pub` line is a single line and matches the private key.  
3. Check ownership/permissions (`700` on `.ssh`, `600` on `authorized_keys`).  
4. On the bastion: `sudo tail -f /var/log/auth.log` (or `journalctl -u ssh`) while connecting.

---

## 4. Get the host key fingerprint (required in the panel)

BaxAuto only accepts the OpenSSH **SHA256** host fingerprint (same idea as `ssh-keygen -lf`).

From a machine that can reach the bastion, run **against the same IP/hostname** you will enter in the form:

```bash
ssh-keyscan -t ed25519,ecdsa,rsa BASTION_IP 2>/dev/null | ssh-keygen -lf -
# Non-default SSH port:
ssh-keyscan -p 2222 -t ed25519,ecdsa,rsa BASTION_IP 2>/dev/null | ssh-keygen -lf -
```

Example output:

```text
256 SHA256:AbCdEfGhIjKlMnOpQrStUvWxYz0123456789abcd BASTION_IP (ED25519)
```

Copy only the fingerprint part into the panel:

```text
SHA256:AbCdEfGhIjKlMnOpQrStUvWxYz0123456789abcd
```

Notes:

- Prefix `SHA256:` is required (or BaxAuto will add it; pasting the full `SHA256:…` value is clearest).  
- Do **not** paste the whole `ssh-keyscan` line (algorithm + host + key blob).  
- The fingerprint must match **that** host. If you change IP/DNS or the host regenerates keys, update the field.  
- Windows (OpenSSH client): the same `ssh-keyscan` / `ssh-keygen` commands work in PowerShell if OpenSSH is installed.

Alternate (after you already trust the host once):

```bash
ssh-keygen -lf <(ssh-keyscan -t ed25519 BASTION_IP 2>/dev/null)
```

---

## 5. Fill the connection form in BaxAuto

1. Open **Databases** → create/edit connection.  
2. Enable **SSH tunnel**.  
3. Set:

| Field | Typical value |
|--------|----------------|
| SSH host | Bastion IP or DNS (must match what you keyscanned) |
| SSH port | `22` unless custom (must match `-p` / `ssh-keyscan -p`) |
| SSH username | e.g. `baxauto` |
| Private key **or** password | Private key PEM contents preferred |
| Host key fingerprint | `SHA256:…` from step 4 |
| DB host | `127.0.0.1` (or private IP **reachable from the bastion**) |
| DB port | Engine port on that host (e.g. `5432`) |

4. Save, then use **Test connection**.

Test reports SSH and DB separately when the tunnel is enabled — fix SSH first if that stage fails.

---

## 6. Checklist when something fails

| Symptom | Likely cause |
|---------|----------------|
| `Permission denied (publickey)` | Public key missing/wrong host; wrong user; bad permissions |
| Fingerprint mismatch | Keyscan was for another IP; host key rotated; pasted wrong field |
| DB connection refused through tunnel | Wrong DB host/port **from bastion’s view**; DB not listening on that interface |
| Timeout to SSH host | Firewall / wrong IP / SSH not listening |

---

## Security notes

- Fingerprint pinning stops silent MITM if DNS/IP is redirected.  
- Prefer a dedicated tunnel user with key-only auth.  
- Do not reuse a personal interactive account’s password in the panel if a key works.  
- Private keys in BaxAuto are stored for the connection owner — treat panel access like secret access.

---

## Related code

- Tunnel implementation: `server/db_connections/ssh_tunnel.py`  
- Connection fields / test: `server/db_connections/` + panel **Databases** form  
