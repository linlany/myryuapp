import time
from itertools import islice
import random

from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import arp
from ryu.topology import event
from ryu.topology.api import get_switch, get_link
import networkx as nx
from ryu.lib import hub
from ryu.lib import mac
from ryu.lib.packet import ipv6, ipv4
from ryu.topology.switches import Switches
from ryu.topology.switches import LLDPPacket
from ryu.base.app_manager import lookup_service_brick
import matplotlib.pyplot as plt
from setting import BandWidth

waite_time = 3
echo_request_break_time = 0.05
max_bw = BandWidth


class MySwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(MySwitch, self).__init__(*args, **kwargs)
        self.group_ids = []
        self.temp_flow_stat = {}
        self.flow_speed = {}
        self.switch_module = lookup_service_brick('switches')
        self.topology_api_app = self
        self.net = nx.DiGraph()
        self.paths = {}
        self.datapaths = []
        self.switch_state = {}
        self.temp_port_stat = {}
        self.arp_record = {}
        self.K = 4
        self.echo_delay = {}
        self.lldp_delay = {}
        self.link_delay = {}
        # self.multi_group_ids = {}
        self.id2dp = {}
        self.elephant_flow = []
        self.monitor_thread = hub.spawn(self.monitor)

    def monitor(self):
        while True:
            self.echo_request()
            for dp in self.datapaths:
                self.switch_state.setdefault(dp.id, {})
                self.get_switch_stat(dp)

                # refresh
                for key in self.paths.keys():
                    self.paths[key] = {}
                # print(self.net.number_of_nodes())
            # nx.draw(self.net)
            # plt.show()
            self.get_delay()
            # self.logger.info(self.link_delay)
            # self.logger.info(self.switch_state)
            self.elephant_flow_multi()
            # self.reseted.clear()
            hub.sleep(waite_time)
        pass

    def echo_request(self):
        for dp in self.datapaths:
            parser = dp.ofproto_parser
            req = parser.OFPEchoRequest(dp, data=bytes("%.12f" % time.time(), encoding="utf8"))
            dp.send_msg(req)
            hub.sleep(echo_request_break_time)

    @set_ev_cls(ofp_event.EventOFPEchoReply, MAIN_DISPATCHER)
    def echo_reply_handler(self, ev):
        now_time = time.time()
        delay = now_time - eval(ev.msg.data)
        self.echo_delay[ev.msg.datapath.id] = delay

    def get_delay(self):
        for key in self.lldp_delay.keys():
            delay = (self.lldp_delay[key] + self.lldp_delay[(key[1], key[0])] - self.echo_delay[key[0]] -
                     self.echo_delay[key[1]]) / 2
            self.link_delay[key] = max(delay, 0)

    def get_switch_stat(self, dp):
        ofproto = dp.ofproto
        parser = dp.ofproto_parser
        req = parser.OFPPortDescStatsRequest(dp, 0)
        dp.send_msg(req)
        req = parser.OFPPortStatsRequest(dp, 0, ofproto.OFPP_ANY)
        dp.send_msg(req)
        req = parser.OFPFlowStatsRequest(dp)
        dp.send_msg(req)
        pass

    def elephant_flow_multi(self):
        self.elephant_flow.clear()
        for flow in list(self.flow_speed.items()):
            dp = flow[0][0]
            dpid = dp.id
            in_port = flow[0][1]
            dst = flow[0][2]
            src_mac = flow[0][4]
            if flow[1]*8 > 0.1*max_bw * 1000000 and (src_mac, dst) not in self.elephant_flow:
                self.elephant_flow.append((src_mac, dst))
            pass

    def install_path_flow(self, path):
        for i in range(len(path)-2, 0, -1):
            last_hop = path[i - 1]
            cur_dp = path[i]
            next_hop = path[i + 1]
            if i == 1:
                in_port = self.net[cur_dp][last_hop]['attr_dict']['port']
            else:
                in_port = self.net[last_hop][cur_dp]['attr_dict']['port']
            out_port = self.net[cur_dp][next_hop]['attr_dict']['port']
            datapath = self.id2dp[cur_dp]
            parser = datapath.ofproto_parser
            actions = [parser.OFPActionOutput(out_port)]
            match = parser.OFPMatch(in_port=in_port, eth_dst=path[-1], eth_src=path[0])
            self.add_flow(datapath, 2, match, actions, idle_timeout=15, hard_timeout=60)
        pass
    # def generate_id(self):
    #     n = random.randint(0, 2**32)
    #     while n in self.group_ids:
    #         n = random.randint(0, 2**32)
    #     self.group_ids.append(n)
    #     return n

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        body = msg.body
        for stat in sorted([flow for flow in body if flow.priority == 1],
                           key=lambda flow: (flow.match.get('in_port'), flow.match.get('eth_dst'))):
            if stat.instructions[0].actions[0].port or stat.instructions[0].actions[0].port == 0:
                key = (dp, stat.match.get('in_port'), stat.match.get('eth_dst'), stat.instructions[0].actions[0].port,
                       stat.match.get('eth_src'))
                now_value = (stat.packet_count, stat.byte_count, stat.duration_sec, stat.duration_nsec)
                self.temp_flow_stat.setdefault(key, ())
                last = 0
                period = waite_time
                temp = self.temp_flow_stat[key]
                if temp:
                    last = temp[1]
                    period = now_value[3] / 10 ** 9 + now_value[2] - temp[2] - temp[3] / 10 ** 9
                self.temp_flow_stat[key] = now_value
                speed = (now_value[1] - last) / period
                self.flow_speed[key] = speed  # byte/s

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        msg = ev.msg
        dpid = msg.datapath.id
        for port in msg.body:
            if port.port_no != ofproto_v1_3.OFPP_LOCAL:
                self.temp_port_stat.setdefault((dpid, port.port_no), ())
                temp = self.temp_port_stat[(dpid, port.port_no)]
                now = (port.tx_bytes, port.rx_bytes, port.duration_sec, port.duration_nsec)
                last = 0
                time = waite_time
                if temp:
                    last = temp[0] + temp[1]
                    time = now[2] + now[3] / 10 ** 9 - temp[2] - temp[3] / 10 ** 9
                speed = (now[0] + now[1] - last) / time
                self.temp_port_stat[(dpid, port.port_no)] = now
                # self.switch_state[dpid][port.port_no]['free_bandwidth'] = \
                #     self.switch_state[dpid][port.port_no]['curr_speed'] / 10 ** 3 - speed * 8 / 10 ** 6
                self.switch_state[dpid][port.port_no]['free_bandwidth'] = max_bw - speed * 8 / 10 ** 6
                self.switch_state[dpid][port.port_no]['speed'] = speed  # byte/s
                # Mbps
        pass

    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_desc_stats_reply_handler(self, ev):
        msg = ev.msg
        dpid = msg.datapath.id
        for port in msg.body:
            if port.port_no != ofproto_v1_3.OFPP_LOCAL:
                self.switch_state[dpid].setdefault(port.port_no, {})
                self.switch_state[dpid][port.port_no]['curr_speed'] = port.curr_speed
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

    def add_flow(self, datapath, priority, match, actions, buffer_id=None, idle_timeout=0, hard_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst, idle_timeout=idle_timeout,
                                    hard_timeout=hard_timeout)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst,
                                    idle_timeout=idle_timeout, hard_timeout=hard_timeout)
        datapath.send_msg(mod)

    @set_ev_cls(event.EventSwitchEnter, [CONFIG_DISPATCHER, MAIN_DISPATCHER])
    def get_topology(self, ev):
        switch_list = get_switch(self.topology_api_app, None)
        dpid_list = [switch.dp.id for switch in switch_list]
        self.datapaths = [switch.dp for switch in switch_list]
        for dp in self.datapaths:
            self.id2dp[dp.id] = dp
        self.net.add_nodes_from(dpid_list)
        link_list = get_link(self.topology_api_app, None)
        links = [(link.src.dpid, link.dst.dpid, {'attr_dict': {'port': link.src.port_no}}) for link in link_list]
        self.net.add_edges_from(links)
        links = [(link.dst.dpid, link.src.dpid, {'attr_dict': {'port': link.dst.port_no}}) for link in link_list]
        self.net.add_edges_from(links)

    def get_bw_delay_range(self, _list):
        minbw = float("inf")
        maxbw = 0
        mindelay = float("inf")
        maxdelay = 0
        for item in _list:
            if item[1] < minbw:
                minbw = item[1]
            if item[1] > maxbw:
                maxbw = item[1]
            if item[2] < mindelay:
                mindelay = item[2]
            if item[2] > maxdelay:
                maxdelay = item[2]
        return minbw, maxbw, mindelay, maxdelay

    def get_outport(self, datapath, src, dst, in_port):
        dpid = datapath.id
        # print(dpid,src,dst)
        if src not in self.net:
            self.net.add_node(src)
            self.net.add_edge(dpid, src, attr_dict={'port': in_port})
            self.net.add_edge(src, dpid)
            self.paths.setdefault(src, {})
        best_path = []
        if dst in self.net:
            if dst not in self.paths[src].keys():
                paths_g = list(islice(nx.shortest_simple_paths(self.net, src, dst), self.K))  # todo: this function is
                # all simple path and
                # k = self.K
                k = 0
                # last_bandwidth = - float("inf")
                last_bandwidth = 0
                K_path = []
                x = hash(src+dst)
                best_path = paths_g[x % len(paths_g)]
                self.paths[src][dst] = best_path
                # self.logger.info("bw: %f, k= %d", min_bandwidth, k)
                # self.logger.info("weight:%f", weight)
                # self.logger.info(best_path)
            else:
                best_path = self.paths[src][dst]
            next_hop = best_path[best_path.index(dpid) + 1]
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

        if pkt.get_protocol(ipv6.ipv6):  # ignore ipv6
            match = parser.OFPMatch(eth_type=eth.ethertype)
            self.add_flow(datapath, 0, match, actions=[])
            return

        arp_ = pkt.get_protocol(arp.arp)
        if arp_ and eth.dst == mac.BROADCAST_STR:
            if (arp_.dst_ip, arp_.src_ip, datapath.id) in self.arp_record:
                if self.arp_record[(arp_.dst_ip, arp_.src_ip, datapath.id)] != in_port:
                    out = parser.OFPPacketOut(datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER,
                                              in_port=in_port, actions=[], data=None)
                    datapath.send_msg(out)
                    return
                else:
                    actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
                    out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                              in_port=in_port, actions=actions, data=msg.data)
                    datapath.send_msg(out)
                    return
            else:
                self.arp_record[(arp_.dst_ip, arp_.src_ip, datapath.id)] = in_port
                actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
                out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                          in_port=in_port, actions=actions, data=msg.data)
                datapath.send_msg(out)
                return

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            s_dpid, s_port_no = LLDPPacket.lldp_parse(msg.data)
            dpid = datapath.id
            if not self.switch_module:
                self.switch_module = lookup_service_brick('switches')
            for port in self.switch_module.ports.keys():
                if s_dpid == port.dpid and s_port_no == port.port_no:
                    delay = self.switch_module.ports[port].delay
                    self.lldp_delay[(s_dpid, dpid)] = delay

            return
        out_port = self.get_outport(datapath, eth.src, eth.dst, in_port)
        # self.logger.info("packet in %s %s %s %s", datapath.id, eth.src, eth.dst, in_port)
        actions = [parser.OFPActionOutput(out_port)]
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=eth.dst, eth_src=eth.src)
            self.add_flow(datapath, 1, match, actions, idle_timeout=0, hard_timeout=0)

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=msg.data)
        datapath.send_msg(out)
        pass
