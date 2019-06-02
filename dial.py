#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Author: Seaky
# @Date:   2019/5/31 16:18


from collections import OrderedDict
from subprocess import PIPE, Popen

import psutil
import xmltodict
from IPy import IP

XMLFILE = 'vpninfo.xml'
'''
edit and save content blew to XMLFILE.

<?xml version="1.0" encoding="utf-8"?>
<info>
    <vpn name="vpn1" server="x.x.x.x" username="username1" password="password1">
        <route>192.168.0.0/24</route>
        <route desc="description">192.168.1.0/24</route>
        <route disable="1">192.168.2.0/24</route>
    </vpn>
    <vpn name="vpn2" server="y.y.y.y" username="username2" password="password2" type="pptp" include_route='vpn1,vpn3'>
        <route>10.0.0.0/24</route>
    </vpn>
    <vpn name="vpn3" server="z.z.z.z" username="username3" password="password3" type="l2tp" disable="1">
        <route>172.16.0.0/24</route>
    </vpn>
</info>
'''


def run_cmd(cmd, stdinstr='', verbose=False):
    p = Popen(cmd, shell=True, universal_newlines=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    outdata, errdata = p.communicate(stdinstr)
    if verbose:
        for s in [p.returncode, outdata, errdata]:
            print(s)
    return p.returncode, outdata, errdata


class VPN:
    def __init__(self):
        self.read() and self.add_route() and self.show() and self.dial() and self.add_route()

    def read(self):
        self.vpns = OrderedDict()
        raw = open(XMLFILE, encoding='utf-8').read()
        for v in xmltodict.parse(raw)['info']['vpn']:
            if not v.get('@disable') == '1':
                self.vpns[v['@name']] = v
        return True

    def get_adpts(self):
        adpts = {}
        for k, v in psutil.net_if_addrs().items():
            for item in v:
                if item[0] == 2 and item[1] != '127.0.0.1':
                    adpts[k] = item[1]
        return adpts

    def show(self):
        s = '''
Choose VPN to connect:\n{}'''.format('\n'.join('  {}. {}'.format(i, name) for i, name in enumerate(self.vpns.keys())))
        print(s)
        select = input('Select or (Q)uit, default is 0: ')
        if not select:
            select = '0'
        elif select.lower() == 'q':
            exit(1)
        if select.isdigit() and int(select) in range(len(self.vpns)):
            self.selection = self.vpns[list(self.vpns.keys())[int(select)]]
            return True
        else:
            print('Selection is illegal!\n\n')
            return self.show()

    def dial(self):
        print('\nStart connect {}...'.format(self.selection['@name']))
        cmd = 'rasdial %s %s %s' % (
            self.selection['@name'], self.selection['@username'], self.selection['@password'])
        returncode, outdata, errdata = run_cmd(cmd)
        if returncode != 0:
            print('connect to vpn {} failed! \n{}'.format(self.selection['@name'], errdata))
            return
        print('Connected.')
        return True

    def add_route(self):
        def add(name, ip):
            routes = self.vpns[name].get('route', [])
            if isinstance(routes, (dict, str)):
                routes = [routes]
            for item in routes:
                if isinstance(item, str):
                    item = {'#text': item}
                if item.get('@disable') == '1' or not item.get('#text'):
                    continue
                rt = IP(item['#text'])
                cmd = 'route add %s mask %s %s' % (rt.net().strFullsize(), rt.netmask().strFullsize(), ip)
                print(cmd)
                returncode, outdata, errdata = run_cmd(cmd)
                print((outdata or errdata).replace('\n', ''))
            for inc in self.vpns[name].get('@include_route', '').split(','):
                if inc in self.vpns:
                    print('\n--- Import route of {} ---'.format(inc))
                    add(inc, ip)

        flag = False
        adpts = self.get_adpts()
        for name, ip in adpts.items():
            if name in self.vpns:
                flag = True
                add(name, ip)
        return not flag


if __name__ == '__main__':
    v = VPN()
    input('\nPress enter to quit.')
