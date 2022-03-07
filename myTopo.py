from mininet.topo import Topo


class MyTopo(Topo):

    def __init__(self):
        Topo.__init__(self)
        # h1 = self.addHost('h1')
        # h2 = self.addHost('h2')
        # h3 = self.addHost('h3')
        # h4 = self.addHost('h4')
        # h5 = self.addHost('h5')
        # h6 = self.addHost('h6')
        # h7 = self.addHost('h7')
        # h8 = self.addHost('h8')
        # h9 = self.addHost('h9')
        # h10 = self.addHost('h10')
        # h11 = self.addHost('h11')
        # h12 = self.addHost('h12')
        # h13 = self.addHost('h13')
        # h14 = self.addHost('h14')
        # h15 = self.addHost('h15')
        # h16 = self.addHost('h16')
        #
        #
        # self.addLink(a_s1, c_s1, bw=1)
        # self.addLink(a_s1, c_s2, bw=1)
        # self.addLink(a_s2, c_s3, bw=1)
        # self.addLink(a_s2, c_s4, bw=1)
        #
        # self.addLink(a_s3, c_s1, bw=1)
        # self.addLink(a_s3, c_s2, bw=1)
        # self.addLink(a_s4, c_s3, bw=1)
        # self.addLink(a_s4, c_s4, bw=1)
        #
        # self.addLink(a_s5, c_s1, bw=1)
        # self.addLink(a_s5, c_s2, bw=1)
        # self.addLink(a_s6, c_s3, bw=1)
        # self.addLink(a_s6, c_s4, bw=1)
        #
        # self.addLink(a_s7, c_s1, bw=1)
        # self.addLink(a_s7, c_s2, bw=1)
        # self.addLink(a_s8, c_s3, bw=1)
        # self.addLink(a_s8, c_s4, bw=1)
        #
        # self.addLink(a_s1, e_s1, bw=1)
        # self.addLink(a_s1, e_s2, bw=1)
        # self.addLink(a_s2, e_s1, bw=1)
        # self.addLink(a_s2, e_s2, bw=1)
        #
        # self.addLink(a_s3, e_s3, bw=1)
        # self.addLink(a_s3, e_s4, bw=1)
        # self.addLink(a_s4, e_s3, bw=1)
        # self.addLink(a_s4, e_s4, bw=1)
        #
        # self.addLink(a_s5, e_s5, bw=1)
        # self.addLink(a_s5, e_s6, bw=1)
        # self.addLink(a_s6, e_s5, bw=1)
        # self.addLink(a_s6, e_s6, bw=1)
        #
        # self.addLink(a_s7, e_s7, bw=1)
        # self.addLink(a_s7, e_s8, bw=1)
        # self.addLink(a_s8, e_s7, bw=1)
        # self.addLink(a_s8, e_s8, bw=1)
        #
        # self.addLink(e_s1, h1, bw=1)
        # self.addLink(e_s1, h2, bw=1)
        # self.addLink(e_s2, h3, bw=1)
        # self.addLink(e_s2, h4, bw=1)
        # self.addLink(e_s3, h5, bw=1)
        # self.addLink(e_s3, h6, bw=1)
        # self.addLink(e_s4, h7, bw=1)
        # self.addLink(e_s4, h8, bw=1)
        # self.addLink(e_s5, h9, bw=1)
        # self.addLink(e_s5, h10, bw=1)
        # self.addLink(e_s6, h11, bw=1)
        # self.addLink(e_s6, h12, bw=1)
        # self.addLink(e_s7, h13, bw=1)
        # self.addLink(e_s7, h14, bw=1)
        # self.addLink(e_s8, h15, bw=1)
        # self.addLink(e_s8, h16, bw=1)
        # for i in range(60):
        #     self.addSwitch('s'+str(i))


topos = {'mytopo': (lambda: MyTopo())}
