# inventory.py

COMMON = {
    "ssh_user": "admin",
    "ssh_password": "admin",
    "_sudo": True,
    "_sudo_password": "admin",
    "nameservers": ["10.0.0.3"],
    "packages": [
        "git",
        "go",
        "iftop",
        "ipmitool",
        "isc-dhcp-server",
        "lynx",
        "mtr",
        "neovim",
        "node_exporter",
        "pftop",
        "python",
        "rsync",
        "sudo",
        "tig",
        "unbound_exporter",
    ],
    "pf_rules": [],
}


routers = (
    [
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
        (
            "clab-pyinfra-routers-lab-router2",
            {
                "interfaces": {
                    "vio1": {
                        "address": "192.168.2.1",
                        "netmask": "255.255.255.0",
                        "description": "LAN router2",
                        "role": "lan",
                    },
                    "vio2": {
                        "address": "10.10.8.2",
                        "netmask": "255.255.255.252",
                        "description": "transit to router1",
                        "role": "transit",
                        "routes": [
                            {"destination": "192.168.1.0/24", "gateway": "10.10.8.1"},
                        ],
                    },
                },
            },
        ),
    ],
    COMMON,
)
