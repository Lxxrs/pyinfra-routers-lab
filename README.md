# pyinfra-routers-lab

## Prequisites

### Install

[`docker`](https://docs.docker.com/engine/install/)

[`containerlab`](https://containerlab.dev/install/)

[`git`](https://git-scm.com/install/linux)

## Usage

### Clone this repository and move into it

```sh
git clone https://codeberg.org/Lxrs/pyinfra-routers-lab.git && cd pyinfra-routers-lab
```

### Run Containerlab

```sh
sudo containerlab deploy -t pyinfra-routers-lab.clab.yml
```

### router1

```sh
ssh clab-pyinfra-routers-lab-router1
sudo ifconfig vio1 192.168.1.1/24
sudo ifconfig vio2 10.10.8.1/30
ping 192.168.1.2
sudo sysctl net.inet.ip.forwarding=1
sudo route add 192.168.2.0/24 10.10.8.2
```

### router2

```sh
ssh clab-pyinfra-routers-lab-router2
sudo ifconfig vio1 192.168.2.1/24
sudo ifconfig vio2 10.10.8.2/30
ping 192.168.2.2
sudo sysctl net.inet.ip.forwarding=1
sudo route add 192.168.1.0/24 10.10.8.1
ping 10.10.8.1
```

### client1

```sh
docker exec -it clab-pyinfra-routers-lab-client1 ash
ping 192.168.2.2
traceroute -n 192.168.2.2
```

### client2

```sh
docker exec -it clab-pyinfra-routers-lab-client2 ash
ping 192.168.1.2
traceroute -n 192.168.1.2
```

#### Many thanks to [Dmitry Teslya](https://dteslya.engineer/blog/2024/03/28/running-bsd-in-containerlab/) for their guidance and contributions
