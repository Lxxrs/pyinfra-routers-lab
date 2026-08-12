# deploy.py

from pyinfra import host
from pyinfra.operations import files, pkg, server

# Resolver
files.template(
    name="Configure resolver",
    src="templates/resolv.conf.j2",
    dest="/etc/resolv.conf",
    mode="644",
)

# Packages
packages = host.data.get("packages", [])
if packages:
    pkg.packages(
        name="Install Packages",
        packages=packages,
        present=True,
    )

# Interfaces
for iface, cfg in host.data.get("interfaces", {}).items():
    iface_file = files.template(
        name=f"Setup interface {iface}",
        src="templates/hostname.if.j2",
        dest=f"/etc/hostname.{iface}",
        mode="640",
        iface=iface,
        cfg=cfg,
    )

    server.shell(
        name=f"Apply interface {iface}",
        commands=[f"sh /etc/netstart {iface}"],
        _if=iface_file.did_change,
    )

# IPv4 Forwarding
server.sysctl(
    name="Enable IPv4 forwarding",
    key="net.inet.ip.forwarding",
    value=1,
    persist=True,
    persist_file="/etc/sysctl.conf",
)

# Packet Filter
pf_conf = files.template(
    name="Render pf ruleset",
    src="templates/pf.conf.j2",
    dest="/etc/pf.conf",
    mode="600",
    pf_rules=host.data.get("pf_rules", []),
)

server.shell(
    name="Validate and load pf ruleset",
    commands=["pfctl -nf /etc/pf.conf && pfctl -f /etc/pf.conf"],
    _if=pf_conf.did_change,
    _ignore_errors=False,
)
