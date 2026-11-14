# pyinfra-routers-lab

A reproducible lab that provisions **OpenBSD routers with [pyinfra](https://pyinfra.com/)**, running on
[Containerlab](https://containerlab.dev/) so it can be spun up on any Linux machine with Docker and KVM.

This is a public, runnable version of my apprenticeship project in which bare-metal OpenBSD routers
are provisioned with pyinfra. The virtualised routers here are configured by the same mechanism as the 
physical ones: agentless SSH, no state on the target, everything in version control.

## Topology

```txt
 ┌─────────┐                  ┌─────────┐                  ┌─────────┐                  ┌─────────┐
 │ client1 │──────────────────│ router1 │══════════════════│ router2 │──────────────────│ client2 │
 │         │                  │ OpenBSD │                  │ OpenBSD │                  │         │
 │ .1.2    │  192.168.1.0/24  │  .1.1   │   10.10.8.0/30   │  .2.1   │  192.168.2.0/24  │  .2.2   │
 └─────────┘             vio1 └─────────┘ vio2        vio2 └─────────┘ vio1             └─────────┘
                                   │        .8.1     .8.2       │
                                   └───────── vio0 ─── vio0 ────┘
                                        management 172.20.20.0/24
```

- **router1 / router2** — OpenBSD 8.0 VMs, each routing its own LAN and peered over a `/30` transit link.
- **client1 / client2** — Alpine containers used to verify the data plane end to end.
- **vio0** on each router is the Containerlab management interface. pyinfra reaches the routers over 
it, and the deploy never touches it.

## Prerequisites

| Tool | Purpose |
| --- | --- |
| [Docker](https://docs.docker.com/engine/install/) | Container runtime for Containerlab |
| [Containerlab](https://containerlab.dev/install/) | Builds the topology |
| [Git](https://git-scm.com/install/linux) | Clone this repository |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Python environment for pyinfra |

Linux only. The OpenBSD nodes run as QEMU VMs inside their containers and need KVM, so nested
virtualisation must be available if you run this inside another VM.

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

From each client, across both routers:

```sh
docker exec -it clab-pyinfra-routers-lab-client1 ash
ping 192.168.2.2
traceroute -n 192.168.2.2
```

`traceroute` should show two hops, confirming both routers forward traffic.

To inspect a router directly (credentials `admin` / `admin`):

```sh
ssh admin@clab-pyinfra-routers-lab-router1
ifconfig vio1
route -n show -inet
sysctl net.inet.ip.forwarding
sudo pfctl -sr
drill @192.168.1.1 openbsd.org
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
| Resolver | `/etc/resolv.conf` pointing at the QEMU DNS forwarder, so `pkg_add` can reach the mirror |
| Packages | Tooling installed with `pkg_add` |
| Interfaces | `/etc/hostname.vioN` per interface, rendered from host data |
| Static routes | `!route add` lines inside the interface files, applied at boot |
| Forwarding | `net.inet.ip.forwarding=1`, persisted in `/etc/sysctl.conf` |
| Packet Filter | The stock OpenBSD ruleset plus per-host rules, validated with `pfctl -n` before loading |
| DNS | `unbound` on loopback and each LAN address, answering only its own LAN subnets |

Interfaces are re-applied with `sh /etc/netstart <iface>` only when the rendered file changes.

## Repository layout

```text
├── pyinfra-routers-lab.clab.yml   # Containerlab topology
├── inventory.py                   # hosts, per-host data, shared group data
├── deploy.py                      # operations applied to every router
├── templates/                     # Jinja templates for the router config files
│   ├── hostname.if.j2              
│   ├── resolv.conf.j2
│   └── unbound.conf.j2
├── cliff.toml                     # changelog generation (git-cliff)
└── CHANGELOG.md
```

## Extending the lab

Router configuration is **data, not code**. Shared settings live in the group data block of
`inventory.py`, and anything unique to one router lives in that host's entry:

```python
(
    "clab-pyinfra-routers-lab-router1",
    {
        "interfaces": {
            "vio1": {
                "address": "192.168.1.1",
                "netmask": "255.255.255.0",
                "description": "LAN router1",
                "role": "lan",
            },
            "vio2": {
                "address": "10.10.8.1",
                "netmask": "255.255.255.252",
                "description": "transit to router2",
                "role": "transit",
                "routes": [
                    {"destination": "192.168.2.0/24", "gateway": "10.10.8.2"},
                ],
            },
        },
    },
),
```

The `role` of an interface drives behaviour: unbound listens on and answers for every `lan` interface.

To add a third router, add the node and its links to the `.clab.yml`, add a host entry with its
addresses to `inventory.py`, and re-run the deploy. `deploy.py` does not change.

## Roadmap

Mirroring the services of the original bare-metal project:

- [x] Interfaces, static routing and forwarding
- [x] `pf` with the stock ruleset
- [x] `unbound` resolver for the LANs
- [ ] `pf` hardened to default-deny, and NAT
- [ ] `kea-dhcp`
- [ ] `ntpd`, `httpd`, `tftpd` / `tftpproxy`, `ftp-proxy`
- [ ] Prometheus exporters (`node_exporter`, `unbound_exporter`, `pf_exporter`)
- [ ] `etckeeper` and a `syspatch` cron job
- [ ] rsync backup integration
- [ ] `nginx` reverse proxy, only on routers that need cross-subnet reachability
- [ ] Automated verification suite (routes, firewall state, DNS answers, exporter endpoints)

## Known issues

**DNS on the management interface.** The image's cloud-init config sets an address and gateway but
no nameserver, so a freshly booted router has an empty `/etc/resolv.conf` and `pkg_add` fails with
`no address associated with name`. The deploy writes the resolver before installing packages.

**sudo, not doas.** OpenBSD ships `doas`, but cloud-init sets the image up with `sudo`, and the deploy
uses it as it is.

**Flavored packages.** `mtr` and `rsync` are left out of the package list. Without a flavor, `pkg_add`
asks which one to install. With a flavor, `pkg.packages` cannot match the installed name and reinstalls
on every run.

**Unknown `TERM`.** Terminals whose terminfo entry OpenBSD does not ship (for example `xterm-ghostty`)
cause `failed termcap lookup` warnings on interactive logins. This is harmless and does not affect
pyinfra runs. Work around it on the client:

```sh
# ~/.ssh/config
Host clab-*
    SetEnv TERM=xterm-256color
```

**Credentials in the inventory.** `inventory.py` contains `admin` / `admin` in plaintext. These are the
image's documented defaults, not secrets: the lab is disposable and only reachable from the host that 
created it. For a real deployment, read them from the environment or use key-based auth with `ssh_key`.

## Further Docs

- [Containerlab](https://containerlab.dev/)
- [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/#summary)
- [git-cliff](https://git-cliff.org/docs/)
- [OpenBSD](https://openbsd.org)
- [OpenBSD Handbook](https://www.openbsdhandbook.com/)
- [Python](https://docs.python.org/3/)
- [pyinfra](https://docs.pyinfra.com/en/3.x/index.html)
- [ruff](https://docs.astral.sh/ruff/)
- [Semantic Versioning](https://semver.org/)
- [ty](https://docs.astral.sh/ty/)
- [uv](https://docs.astral.sh/uv/)

## Credits

Thanks to [Dmitry Teslya](https://github.com/dteslya) for the OpenBSD Containerlab integration and 
[guidance](https://dteslya.engineer/blog/2024/03/28/running-bsd-in-containerlab/) on running OpenBSD in 
Containerlab, and for the prebuilt images this lab started with.

## License
[ISC](LICENSE)
