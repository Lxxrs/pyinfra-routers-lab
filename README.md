# pyinfra-routers-lab

A reproducible lab that provisions **OpenBSD routers with [pyinfra](https://pyinfra.com/)**, running on
[Containerlab](https://containerlab.dev/) so it can be spun up on any Linux machine with Docker.

This is a public, runnable version of my apprenticeship project in which bare-metal OpenBSD routers
are provisioned with pyinfra. The virtualised routers here are configured by exactly the same
mechanism as the physical ones: agentless SSH, no state on the target, everything in version control.

## Topology

```sh
 ┌─────────┐                  ┌─────────┐                  ┌─────────┐                  ┌─────────┐
 │ client1 │──────────────────│ router1 │══════════════════│ router2 │──────────────────│ client2 │
 │         │                  │ OpenBSD │                  │ OpenBSD │                  │         │
 │ .1.2    │  192.168.1.0/24  │  .1.1   │   10.10.8.0/30   │  .2.1   │  192.168.2.0/24  │  .2.2   │
 └─────────┘             vio1 └─────────┘ vio2        vio2 └─────────┘ vio1             └─────────┘
                                   │        .8.1     .8.2       │
                                   └───────── vio0 ─── vio0 ────┘
                                        management 172.20.20.0/24
```

- **router1 / router2** — OpenBSD 7.8 VMs, each routing its own LAN and peered over a `/30` transit link.
- **client1 / client2** — Alpine containers used to verify the data plane end to end.
- **vio0** on each router is the Containerlab management interface. pyinfra reaches the routers over it;
  it is never touched by the deploy.

## Prerequisites

| Tool | Purpose |
| --- | --- |
| [Docker](https://docs.docker.com/engine/install/) | container runtime for Containerlab |
| [Containerlab](https://containerlab.dev/install/) | builds the topology |
| [Git](https://git-scm.com/install/linux) | clone this repository |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Python environment for pyinfra |

Linux only. The OpenBSD nodes run as QEMU VMs inside their containers and need KVM, so nested
virtualisation must be available if you are running this inside another VM.

## Usage

### 1. Clone this repo

```sh
git clone https://codeberg.org/Lxrs/pyinfra-routers-lab.git && cd pyinfra-routers-lab
```

### 2. Start the lab

```sh
sudo containerlab deploy -t pyinfra-routers-lab.clab.yml
```

The OpenBSD nodes take roughly 1–2 minutes to boot. Wait until both report `healthy`:

```sh
sudo containerlab inspect -t pyinfra-routers-lab.clab.yml
```

### 3. Provision the routers

```sh
uv sync
uv run pyinfra -y inventory.py deploy.py
```

The inventory must come first — pyinfra takes the first argument as the inventory and everything
after it as deploy code.

### 4. Verify

From the clients, across both routers:

```sh
docker exec -it clab-pyinfra-routers-lab-client1 ash
ping 192.168.2.2
traceroute -n 192.168.2.2
```

```sh
docker exec -it clab-pyinfra-routers-lab-client2 ash
ping 192.168.1.2
traceroute -n 192.168.1.2
```

`traceroute` should show two hops, confirming both routers forward traffic.

To inspect a router directly (credentials `admin` / `admin`):

```sh
ssh admin@clab-pyinfra-routers-lab-router1
ifconfig vio1
route -n show -inet
sysctl net.inet.ip.forwarding
```

### 5. Tear down

```sh
sudo containerlab destroy -t pyinfra-routers-lab.clab.yml --cleanup
```

## Dev

### Audit dependencies for vulnerabilities

```sh
uv audit
```

### Install dev dependencies

```sh
uv sync --group dev
```

### Upgrade dependencies

```sh
uv lock --upgrade
```

### Lint

```sh
uv run ruff check .
uv run ruff check . --fix
```

### Format

```sh
uv run ruff format .
```

### Typecheck

```sh
uv run ty check .
```

### Run all checks

```sh
uv run ruff check . && uv run ruff format . --check && uv run ty check .
```

## What the deploy configures

| Step | Result |
| --- | --- |
| Resolver | `/etc/resolv.conf` pointing at the QEMU DNS forwarder, so `pkg_add` can resolve the mirror |
| Base packages | Install tooling with `pkg_add` |
| Interfaces | `/etc/hostname.vioN` per interface, rendered from host data |
| Static routes | `!route add` lines inside the interface files, applied at boot |
| Forwarding | `net.inet.ip.forwarding=1`, persisted in `/etc/sysctl.conf` |

Interfaces are applied with `sh /etc/netstart <iface>` only when the rendered file actually changes,
so repeat runs are idempotent and do not bounce links.

## Repository layout

```sh
├── pyinfra-routers-lab.clab.yml   # Containerlab topology
├── inventory.py                   # hosts, per-host data, shared group data
├── deploy.py                      # operations applied to every router
└── templates/
    ├── hostname.if.j2             # /etc/hostname.vioN
    └── resolv.conf.j2             # /etc/resolv.conf
```

## Extending the lab

Router configuration is **data, not code**. Shared settings live in the group data block of
`inventory.py`; anything unique to one router lives in that host's own dictionary:

```python
(
    (
        "clab-pyinfra-routers-lab-router1",
        {
            "interfaces": {
                "vio1": {
                    "address": "192.168.1.1",
                    "netmask": "255.255.255.0",
                    "description": "LAN router1",
                },
                "vio2": {
                    "address": "10.10.8.1",
                    "netmask": "255.255.255.252",
                    "description": "transit to router2",
                    "routes": [
                        {"destination": "192.168.2.0/24", "gateway": "10.10.8.2"},
                    ],
                },
            },
        },
    ),
)
```

To add a third router: add the node and its links to the `.clab.yml`, add a host entry with its
addresses to `inventory.py`, and re-run the deploy. `deploy.py` does not change.

Optional services follow the same principle — the operations exist for every router but only run
where the data asks for them:

```python
if host.data.get("enable_nginx", False):
    ...
```

## Roadmap

Mirroring the services from the original bare-metal project:

- [ ] `pf` firewall and NAT
- [ ] `unbound` resolver
- [ ] `kea-dhcp`
- [ ] `ntpd`, `httpd`, `tftpd` / `tftpproxy`, `ftpproxy`
- [ ] Prometheus exporters (`node_exporter`, `unbound_exporter`, `pf_exporter`)
- [ ] `etckeeper` and a `syspatch` cron job
- [ ] rsync backup integration
- [ ] `nginx` reverse proxy, deployed only on routers that need cross-subnet reachability
- [ ] automated verification suite (assert routes, firewall state and exporter endpoints)

## Notes and known issues

**OpenBSD 7.8, not 7.9.** The 7.9 cloud image fails to provision its login credentials via cloud-init
([hcartiaux/openbsd-cloud-image#15](https://github.com/hcartiaux/openbsd-cloud-image/issues/15)) —
the node boots and reports healthy, but no working account exists. 7.8 is unaffected.

**Prebuilt node image.** The topology pulls
`ghcr.io/dteslya/vrnetlab-images/openbsd-vrnetlab:7.8` directly, so there is no need to build a
vrnetlab image from a qcow2 locally. This removes the largest reproducibility hurdle, at the cost of
depending on an external registry.

**DNS on the management interface.** The vrnetlab cloud-init config sets an address and gateway but
no nameserver, so a freshly booted router has an empty `/etc/resolv.conf` and `pkg_add` fails with
`no address associated with name`. The deploy writes the resolver before touching packages.

**sudo, not doas.** Real OpenBSD ships `doas`; this cloud image is set up with `sudo` by cloud-init
and the deploy uses it as-is.

**Unknown `TERM`.** Terminals whose terminfo entry OpenBSD does not ship (e.g. `xterm-ghostty`)
produce `failed termcap lookup` warnings on interactive logins. Harmless, and not present in pyinfra
runs. Work around it client-side:

```sh
# ~/.ssh/config
Host clab-*
    SetEnv TERM=xterm-256color
```

**Credentials in the inventory.** `inventory.py` contains `admin` / `admin` in plaintext. These are
the documented defaults of the public vrnetlab OpenBSD image, not secrets — the lab is disposable and
reachable only from the host that created it. For anything real, source them from the environment
instead:

```python
import os

COMMON = {
    "ssh_user": os.environ.get("ROUTER_USER", "admin"),
    "ssh_password": os.environ["ROUTER_PASSWORD"],
}
```

or drop passwords entirely in favour of key-based auth with `ssh_key`.

## Further Docs

- [Containerlab](https://containerlab.dev/)
- [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/#summary)
- [git-cliff](https://git-cliff.org/docs/)
- [Python](https://docs.python.org/3/)
- [pyinfra](https://docs.pyinfra.com/en/3.x/index.html)
- [ruff](https://docs.astral.sh/ruff/)
- [Semantic Versioning](https://semver.org/)
- [ty](https://docs.astral.sh/ty/)
- [uv](https://docs.astral.sh/uv/)

## Credits

Many thanks to [Dmitry Teslya](https://github.com/dteslya) for the OpenBSD Containerlab integration,
providing of [prebuilt node images](https://github.com/dteslya/vrnetlab-images/pkgs/container/vrnetlab-images%2Fopenbsd-vrnetlab)
and [guidance](https://dteslya.engineer/blog/2024/03/28/running-bsd-in-containerlab/) for running OpenBSD in Containerlab.
