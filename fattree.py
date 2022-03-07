from mininet.node import RemoteController
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink

K = 4
bw_ca = 1
bw_ae = 1
bw_eh = 1


class fattree(Topo):
    def __init__(self, *args, **params):
        super().__init__(*args, **params)
        self.hostlist = []
        self.corelist = []
        self.aggregatelist = []
        self.edgelist = []

    def creat_topo(self):
        n = (K / 2) ** 2  # core
        for i in range(int(n)):
            self.corelist.append(self.addSwitch('core_s' + str(i)))
        n = K * K / 2  # k pod
        for i in range(int(n)):
            self.aggregatelist.append(self.addSwitch('agg_s' + str(i)))
            self.edgelist.append(self.addSwitch('edg_s' + str(i)))
        n = n * K / 2  # host
        for i in range(int(n)):
            self.hostlist.append(self.addHost('h' + str(i)))
        n = K * K // 2
        step = K // 2
        for i in range(0, n, step):
            for j in range(step):
                for k in range(step):
                    self.addLink(self.aggregatelist[i + j], self.corelist[j * step + k], bw=bw_ca)
                    self.addLink(self.aggregatelist[i + j], self.edgelist[i + k], bw=bw_ae)
        for i in range(n):
            for j in range(step):
                self.addLink(self.edgelist[i], self.hostlist[step * i + j], bw=bw_eh)


def creat_fattree():
    topo = fattree()
    topo.creat_topo()
    net = Mininet(topo=topo, link=TCLink, controller=None, autoSetMacs=True)
    net.addController(
        'controller', controller=RemoteController,
        ip="127.0.0.1", port=6633)
    net.start()


creat_fattree()
