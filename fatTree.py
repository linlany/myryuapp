from mininet.topo import Topo

K = 4
bw_ca = 1
bw_ae = 1
bw_eh = 1
delay = '5ms'

class MyTopo(Topo):
    # hostlist = []
    # corelist = []
    # aggregatelist = []
    # edgelist = []

    def __init__(self):
        Topo.__init__(self)
        self.hostlist = []
        self.corelist = []
        self.aggregatelist = []
        self.edgelist = []
        self.creat_topo()

    def creat_topo(self):
        n = (K // 2) ** 2  # core
        for i in range(int(n)):
            if i < 10:
                self.corelist.append(self.addSwitch('core_s30' + str(i)))
            else:
                self.corelist.append(self.addSwitch('core_s3' + str(i)))
        n = K * K // 2  # k pod
        for i in range(int(n)):
            if i < 10:
                self.aggregatelist.append(self.addSwitch('agg_s20' + str(i)))
                self.edgelist.append(self.addSwitch('edg_s10' + str(i)))
            else:
                self.aggregatelist.append(self.addSwitch('agg_s2' + str(i)))
                self.edgelist.append(self.addSwitch('edg_s1' + str(i)))
        n = K * K // 2 * K // 2  # host
        for i in range(int(n)):
            if i < 10:
                self.hostlist.append(self.addHost('h00' + str(i)))
            else:
                self.hostlist.append(self.addHost('h0' + str(i)))
        n = K * K // 2
        step = K // 2
        for i in range(0, n, step):
            for j in range(step):
                for k in range(step):
                    self.addLink(self.aggregatelist[i + j], self.corelist[j * step + k], bw=bw_ca, delay=delay)
                    self.addLink(self.aggregatelist[i + j], self.edgelist[i + k], bw=bw_ae, delay=delay)
        for i in range(n):
            for j in range(step):
                self.addLink(self.edgelist[i], self.hostlist[step * i + j], bw=bw_eh, delay=delay)

    # def creat_switch(self, n, pre, slist):
    #     for i in range(int(n)):
    #         slist.append(self.addSwitch(pre + str(i)))


topos = {'mytopo': (lambda: MyTopo())}
