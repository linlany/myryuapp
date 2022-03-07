from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.topology import event
from ryu.topology.api import get_switch, get_link
import networkx as nx


class MySwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(MySwitch, self).__init__(*args, **kwargs)
        self.topology_api_app = self
        self.net = nx.DiGraph()
        self.paths = {}
        pass

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(event.EventSwitchEnter, [CONFIG_DISPATCHER, MAIN_DISPATCHER])
    def get_topology(self, ev):
        switch_list = get_switch(self.topology_api_app, None)
        switch_id = [switch.dp.id for switch in switch_list]
        self.net.add_nodes_from(switch_id)
        link_list = get_link(self.topology_api_app, None)
        links = [(link.src.dpid, link.dst.dpid, {'attr_dict':{'port':link.src.port_no}}) for link in link_list]
        self.net.add_edges_from(links)
        links = [(link.dst.dpid, link.src.dpid, {'attr_dict':{'port':link.dst.port_no}}) for link in link_list]
        self.net.add_edges_from(links)

    def get_outport(self, datapath, src, dst, in_port):
        dpid = datapath.id
        # print(dpid,src,dst)
        if src not in self.net:
            self.net.add_node(src)
            self.net.add_edge(dpid, src, attr_dict={'port': in_port})
            self.net.add_edge(src, dpid)
            self.paths.setdefault(src, {})
        if dst in self.net:
            if dst not in self.paths[src]:
                path = nx.shortest_path(self.net, src, dst)
                self.paths[src][dst] = path
            else:
                path = self.paths[src][dst]
            print(path)
            next_hop = path[path.index(dpid) + 1]
            out_port = self.net[dpid][next_hop]['attr_dict']['port']
        else:
            out_port = datapath.ofproto.OFPP_FLOOD
        return out_port

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        # info
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        out_port = self.get_outport(datapath, eth.src, eth.dst, in_port)
        # self.logger.info("packet in %s %s %s %s", datapath.id, eth.src, eth.dst, in_port)
        actions = [parser.OFPActionOutput(out_port)]
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=eth.dst)
            self.add_flow(datapath, 1, match, actions)

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=msg.data)
        datapath.send_msg(out)
        pass
