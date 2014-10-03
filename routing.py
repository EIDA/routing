#!/usr/bin/env python
#
# Routing WS prototype
#
# (c) 2014 Javier Quinteros, GEOFON team
# <javier@gfz-potsdam.de>
#
# ----------------------------------------------------------------------

"""Routing Webservice for EIDA

(c) 2014 Javier Quinteros, GEOFON, GFZ Potsdam

Encapsulate and manage routing information of networks,
stations, locations and streams read from an XML file.

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2, or (at your option) any later
version. For more information, see http://www.gnu.org/

"""

##################################################################
#
# First all the imports
#
##################################################################


import os
import cgi
import datetime
import fnmatch
import json
import telnetlib
import xml.etree.cElementTree as ET
from time import sleep
from collections import namedtuple
from inventorycache import InventoryCache
from wsgicomm import WIContentError
from wsgicomm import WIClientError
from wsgicomm import WIError
from wsgicomm import send_plain_response
# from wsgicomm import send_html_response
from wsgicomm import send_xml_response


def _ConvertDictToXmlRecurse(parent, dictitem):
    assert not isinstance(dictitem, list)

    if isinstance(dictitem, dict):
        for (tag, child) in dictitem.iteritems():
            if str(tag) == '_text':
                parent.text = str(child)
            elif isinstance(child, list):
                # iterate through the array and convert
                for listchild in child:
                    elem = ET.Element(tag)
                    parent.append(elem)
                    _ConvertDictToXmlRecurse(elem, listchild)
            else:
                elem = ET.Element(tag)
                parent.append(elem)
                _ConvertDictToXmlRecurse(elem, child)
    else:
        parent.text = str(dictitem)


def ConvertDictToXml(listdict):
    """
    Converts a list with dictionaries to an XML ElementTree Element
    """

    r = ET.Element('service')
    for di in listdict:
        d = {'datacenter': di}
        roottag = d.keys()[0]
        root = ET.SubElement(r, roottag)
        _ConvertDictToXmlRecurse(root, d[roottag])
    return r


class RouteSL(namedtuple('RouteSL', ['address', 'priority'])):
    __slots__ = ()

RouteSL.__eq__ = lambda self, other: self.priority == other.priority
RouteSL.__ne__ = lambda self, other: self.priority != other.priority
RouteSL.__lt__ = lambda self, other: self.priority < other.priority
RouteSL.__le__ = lambda self, other: self.priority <= other.priority
RouteSL.__gt__ = lambda self, other: self.priority > other.priority
RouteSL.__ge__ = lambda self, other: self.priority >= other.priority


class Route(namedtuple('Route', ['address', 'start', 'end', 'priority'])):
    __slots__ = ()

    def __contains__(self, pointTime):
        if pointTime is None:
            return True

        try:
            if (((self.start <= pointTime) or (self.start is None)) and
                    ((pointTime <= self.end) or (self.end is None))):
                return True
        except:
            pass
        return False

Route.__eq__ = lambda self, other: self.priority == other.priority
Route.__ne__ = lambda self, other: self.priority != other.priority
Route.__lt__ = lambda self, other: self.priority < other.priority
Route.__le__ = lambda self, other: self.priority <= other.priority
Route.__gt__ = lambda self, other: self.priority > other.priority
Route.__ge__ = lambda self, other: self.priority >= other.priority


class RouteMT(namedtuple('RouteMT', ['address', 'start', 'end', 'priority',
                                     'service'])):
    __slots__ = ()

    def __contains__(self, pointTime):
        if pointTime is None:
            return True

        try:
            if (((self.start <= pointTime) or (self.start is None)) and
                    ((pointTime <= self.end) or (self.end is None))):
                return True
        except:
            pass
        return False

RouteMT.__eq__ = lambda self, other: self.priority == other.priority
RouteMT.__ne__ = lambda self, other: self.priority != other.priority
RouteMT.__lt__ = lambda self, other: self.priority < other.priority
RouteMT.__le__ = lambda self, other: self.priority <= other.priority
RouteMT.__gt__ = lambda self, other: self.priority > other.priority
RouteMT.__ge__ = lambda self, other: self.priority >= other.priority


class RoutingException(Exception):
    pass


class RoutingCache(object):
    """Encapsulate and manage routing information of networks,
    stations, locations and streams read from an Arclink XML file.

    Begun by Javier Quinteros <javier@gfz-potsdam.de>, GEOFON team, June 2014

    """

    def __init__(self, routingFile, invFile, masterFile=None):
        # Arclink routing file in XML format
        self.routingFile = routingFile

        # Dictionary with all the routes
        self.routingTable = dict()

        # Dictionary with the seedlink routes
        self.slTable = dict()

        # Dictionary with the FDSN-WS station routes
        self.stTable = dict()

        # Create/load the cache the first time that we start
        if routingFile == 'auto':
            self.configArclink()
            self.routingFile = './routing.xml'

        try:
            self.update()
        except:
            self.configArclink()
            self.update()

        if masterFile is None:
            return

        # Master routing file in XML format
        self.masterFile = masterFile

        # Dictionary with list of highest priority routes
        self.masterTable = dict()

        self.updateMT()

        # Add inventory cache here, to be accessible to all modules
        self.ic = InventoryCache(invFile)

    def localConfig(self):
        here = os.path.dirname(__file__)

        with open(os.path.join(here, 'routing.xml')) as f:
            return f.read()

    def configArclink(self, arcServ='eida.gfz-potsdam.de', arcPort=18002):
        tn = telnetlib.Telnet(arcServ, arcPort)
        tn.write('HELLO\n')
        # FIXME The institution should be detected here. Shouldn't it?
        print tn.read_until('GFZ')
        tn.write('user routing@eida\n')
        print tn.read_until('OK', 5)
        tn.write('request routing\n')
        print tn.read_until('OK', 5)
        tn.write('1920,1,1,0,0,0 2030,1,1,0,0,0 * * * *\nEND\n')

        reqID = 0
        while not reqID:
            text = tn.read_until('\n', 5).splitlines()
            for line in text:
                try:
                    testReqID = int(line)
                except:
                    continue
                if testReqID:
                    reqID = testReqID

        myStatus = 'UNSET'
        while (myStatus in ('UNSET', 'PROCESSING')):
            sleep(1)
            tn.write('status %s\n' % reqID)
            stText = tn.read_until('END', 5)

            stStr = 'status='
            myStatus = stText[stText.find(stStr) + len(stStr):].split()[0]
            myStatus = myStatus.replace('"', '').replace("'", "")
            print myStatus

        if myStatus != 'OK':
            print 'Error! Request status is not OK.'
            return

        tn.write('download %s\n' % reqID)
        routTable = tn.read_until('END', 5)
        start = routTable.find('<')
        print 'Length:', routTable[:start]
        try:
            os.remove('./routing.xml.download')
        except:
            pass

        here = os.path.dirname(__file__)

        with open(os.path.join(here, 'routing.xml.download'), 'w') as fout:
            fout.write(routTable[routTable.find('<'):-3])

        try:
            os.rename(os.path.join(here, './routing.xml'),
                      os.path.join(here, './routing.xml.bck'))
        except:
            pass

        try:
            os.rename(os.path.join(here, './routing.xml.download'),
                      os.path.join(here, './routing.xml'))
        except:
            pass

        print 'Configuration read from Arclink!'

    def __arc2DS(self, route):
        """Map from an Arclink address to a Dataselect one."""

        gfz = 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query'
        odc = 'http://www.orfeus-eu.org/fdsnws/dataselect/1/query'
        eth = 'http://eida.ethz.ch/fdsnws/dataselect/1/query'
        resif = 'http://ws.resif.fr/fdsnws/dataselect/1/query'
        ingv = 'http://webservices.rm.ingv.it/fdsnws/dataselect/1/query'
        bgr = 'http://eida.bgr.de/fdsnws/dataselect/1/query'
        lmu = 'http://erde.geophysik.uni-muenchen.de:8080/fdsnws/' +\
            'dataselect/1/query'
        # iris = 'http://service.iris.edu/fdsnws/dataselect/1/query'

        # Try to identify the hosting institution
        host = route.split(':')[0]

        if host.endswith('gfz-potsdam.de'):
            return gfz
        elif host.endswith('knmi.nl'):
            return odc
        elif host.endswith('ethz.ch'):
            return eth
        elif host.endswith('resif.fr'):
            return resif
        elif host.endswith('ingv.it'):
            return ingv
        elif host.endswith('bgr.de'):
            return bgr
        elif host.startswith('141.84.'):
            return lmu
        return None

    def getRoute(self, n='*', s='*', l='*', c='*', startD=None, endD=None,
                 service='dataselect', alternative=False):
        """getRoute receives a stream and a timewindow and returns a list.
        The list has the following format:
            [[URL_1, net_1, sta_1, loc_1, cha_1, tfrom_1, tto_1],
            ...
             [URL_n, net_n, sta_n, loc_n, cha_n, tfrom_n, tto_n]]
        """

        # Give priority to the masterTable!
        try:
            masterRoute = self.getRouteMaster(n, startD=startD, endD=endD,
                                              service=service,
                                              alternative=alternative)
            for mr in masterRoute:
                for reqL in mr['params']:
                    reqL['sta'] = s
                    reqL['loc'] = l
                    reqL['cha'] = c
            return masterRoute
        except:
            pass

        if service == 'arclink':
            return self.getRouteArc(n, s, l, c, startD, endD, alternative)
        elif service == 'dataselect':
            return self.getRouteDS(n, s, l, c, startD, endD, alternative)
        elif service == 'seedlink':
            return self.getRouteSL(n, s, l, c)
        elif service == 'station':
            return self.getRouteST(n, s, l, c, startD, endD)

        # Through an exception if there is an error
        raise RoutingException('Unknown service: %s' % service)

    def getRouteST(self, n='*', s='*', l='*', c='*',
                   startD=None, endD=None):
        """Use the Dataselect implementation and map to Station-WS.
"""

        result = self.getRouteDS(n, s, l, c, startD, endD)
        for item in result:
            item['name'] = 'station'
            item['url'] = item['url'].replace('dataselect', 'station')

        return result

    def getRouteDS(self, n='*', s='*', l='*', c='*',
                   startD=None, endD=None, alternative=False):
        """Use the table lookup from Arclink to route the Dataselect service
"""

        result = []

        # Check if there are wildcards!
        if (('*' in n + s + l + c) or ('?' in n + s + l + c)):
            # Filter first by the attributes without wildcards

            # Check for the timewindow
            subs = self.routingTable.keys()

            if (('*' not in s) and ('?' not in s)):
                subs = [k for k in subs if (k[1] is None or k[1] == '*' or
                                            k[1] == s)]

            if (('*' not in n) and ('?' not in n)):
                subs = [k for k in subs if (k[0] is None or k[0] == '*' or
                                            k[0] == n)]

            if (('*' not in c) and ('?' not in c)):
                subs = [k for k in subs if (k[3] is None or k[3] == '*' or
                                            k[3] == c)]

            if (('*' not in l) and ('?' not in l)):
                subs = [k for k in subs if (k[2] is None or k[2] == '*' or
                                            k[2] == l)]

            # Filter then by the attributes WITH wildcards
            if (('*' in s) or ('?' in s)):
                subs = [k for k in subs if (k[1] is None or k[1] == '*' or
                                            fnmatch.fnmatch(k[1], s))]

            if (('*' in n) or ('?' in n)):
                subs = [k for k in subs if (k[0] is None or k[0] == '*' or
                                            fnmatch.fnmatch(k[0], n))]

            if (('*' in c) or ('?' in c)):
                subs = [k for k in subs if (k[3] is None or k[3] == '*' or
                                            fnmatch.fnmatch(k[3], c))]

            if (('*' in l) or ('?' in l)):
                subs = [k for k in subs if (k[2] is None or k[2] == '*' or
                                            fnmatch.fnmatch(k[2], l))]

            resSet = set()
            for k in subs:
                # ONLY the first component of the tuple!!!
                # print k, self.routingTable[k]
                bestPrio = None
                for rou in self.routingTable[k]:
                    # Check that the timewindow is OK
                    if (((rou[2] is None) or (startD is None) or
                            (startD < rou[2])) and
                            ((endD is None) or (endD > rou[1]))):
                        # FIXME I think that I don't need bestPrio because the
                        # routes are already sorted by priority
                        if alternative:
                            host = self.__arc2DS(rou[0])
                            resSet.add(host)
                        elif ((bestPrio is None) or (rou[3] < bestPrio)):
                            bestPrio = rou[3]
                            host = self.__arc2DS(rou[0])
                resSet.add(host)

            # Check the coherency of the routes to set the return code
            if len(resSet) == 0:
                raise WIContentError('No routes have been found!')
            elif len(resSet) == 1:
                return [{'name': 'dataselect', 'url': resSet.pop(),
                         'params': [{'net': n, 'sta': s, 'loc': l, 'cha': c,
                                     'start': '' if startD is None else startD,
                                     'end': '' if endD is None else endD}]}]
            else:
                # Alternative NEW approach based on number of wildcards
                order = [sum([1 for t in r if '*' in t]) for r in subs]

                orderedSubs = [x for (y, x) in sorted(zip(order, subs))]

                finalset = list()

                for r1 in orderedSubs:
                    for r2 in finalset:
                        if self.__overlap(r1, r2):
                            print 'Overlap between %s and %s' % (r1, r2)
                            break
                    else:
                        # print 'Adding', r1
                        finalset.append(r1)
                        continue

                    # The break from 10 lines above jumps until this line in
                    # order to do an expansion and try to add the expanded
                    # streams
                    r1n, r1s, r1l, r1c = r1
                    for rExp in self.ic.expand(r1n, r1s, r1l, r1c,
                                               startD, endD, True):
                        for r3 in finalset:
                            if self.__overlap(rExp, r3):
                                print 'Stream %s discarded! Overlap with %s' \
                                    % (rExp, r3)
                                break
                        else:
                            # print 'Adding expanded', rExp
                            if (fnmatch.fnmatch(rExp[0], n) and
                                    fnmatch.fnmatch(rExp[1], s) and
                                    fnmatch.fnmatch(rExp[2], l) and
                                    fnmatch.fnmatch(rExp[3], c)):
                                finalset.append(rExp)

                # In finalset I have all the streams (including expanded and
                # the ones with wildcards), that I need to request.
                # Now I need the URLs
                result = list()
                for st in finalset:
                    # FIXME There is an assumption that getRouteArc will return
                    # only one route, BUT if alternative is True this is not
                    # right!
                    result = self.getRouteArc(st[0], st[1], st[2], st[3],
                                              startD, endD, alternative)
                    for rou in result:
                        rou['url'] = self.__arc2DS(rou['url'])
                        rou['service'] = 'dataselect'

                return result

            raise Exception('This point should have never been reached! ;-)')

        # If there are NO wildcards
        result = self.getRouteArc(n, s, l, c, startD, endD, alternative)

        for rou in result:
            rou['url'] = self.__arc2DS(rou['url'])
            rou['service'] = 'dataselect'

        return result

    def __overlap(self, st1, st2):
        """Checks if there is an overlap between the two set of streams

        Both parameters are expected to have four components:
            network, station, location, channel.
        However, as wildcards are also accepted, these could be actually
        sets of streams. F.i. [GE, None, None, None]"""

        for i in range(len(st1)):
            if ((st1[i] is not None) and (st2[i] is not None) and
                    not fnmatch.fnmatch(st1[i], st2[i]) and
                    not fnmatch.fnmatch(st2[i], st1[i])):
                return False
        return True

    def getRouteMaster(self, n, startD=None, endD=None, service='dataselect',
                       alternative=False):
        """Implement the following table lookup for the Master Table

        11 NET --- --- ---
"""

        result = list()
        realRoutes = None

        # Case 11
        if (n, None, None, None) in self.masterTable:
            realRoutes = self.masterTable[n, None, None, None]

        # Check that I found a route
        for r in realRoutes:
            # Check if the timewindow is encompassed in the returned dates
            if ((startD in r) or (endD in r)):
            #if (((r[2] is None) or (startD is None) or
            #        (startD < r[2])) and
            #        ((endD is None) or (endD > r[1]))):
                # Filtering with the service parameter!
                if service == r.service:
                    result.append(r)
                    if not alternative:
                        break

        # If I found nothing raise 204
        if not len(result):
            raise WIContentError('No routes have been found!')

        result = sorted(result, key=lambda res: res.address)

        result2 = list()
        before = None
        for r in result:
            if before != r.address:
                result2.append({'name': service, 'url': r.address,
                                'params': [{'net': n, 'sta': None,
                                            'loc': None, 'cha': None,
                                            'start': startD if startD is not
                                            None else '',
                                            'end': endD if endD is not None
                                            else '', 'priority': r.priority}]})
                before = r.address
            else:
                result2[-1].params.append({'net': n, 'sta': None,
                                           'loc': None, 'cha': None,
                                           'start': startD if startD is not
                                           None else '',
                                           'end': endD if endD is not None
                                           else '', 'priority': r.priority})

        return result2

    def getRouteSL(self, n, s, l, c):
        """Implement the following table lookup for the Seedlink service

        01 NET STA CHA LOC # First try to match all.
        02 NET STA CHA --- # Then try to match all excluding location,
        03 NET STA --- LOC # ... and so on
        04 NET --- CHA LOC
        05 --- STA CHA LOC
        06 NET STA --- ---
        07 NET --- CHA ---
        08 NET --- --- LOC
        09 --- STA CHA ---
        09 --- STA --- LOC
        10 --- --- CHA LOC
        11 NET --- --- ---
        12 --- STA --- ---
        13 --- --- CHA ---
        14 --- --- --- LOC
        15 --- --- --- ---
"""

        realRoute = None

        # Case 1
        if (n, s, l, c) in self.slTable:
            realRoute = self.slTable[n, s, l, c]

        # Case 2
        elif (n, s, '*', c) in self.slTable:
            realRoute = self.slTable[n, s, '*', c]

        # Case 3
        elif (n, s, l, '*') in self.slTable:
            realRoute = self.slTable[n, s, l, '*']

        # Case 4
        elif (n, '*', l, c) in self.slTable:
            realRoute = self.slTable[n, '*', l, c]

        # Case 5
        elif ('*', s, l, c) in self.slTable:
            realRoute = self.slTable['*', s, l, c]

        # Case 6
        elif (n, s, '*', '*') in self.slTable:
            realRoute = self.slTable[n, s, '*', '*']

        # Case 7
        elif (n, '*', '*', c) in self.slTable:
            realRoute = self.slTable[n, '*', '*', c]

        # Case 8
        elif (n, '*', l, '*') in self.slTable:
            realRoute = self.slTable[n, '*', l, '*']

        # Case 9
        elif ('*', s, '*', c) in self.slTable:
            realRoute = self.slTable['*', s, '*', c]

        # Case 10
        elif ('*', '*', l, c) in self.slTable:
            realRoute = self.slTable['*', '*', l, c]

        # Case 11
        elif (n, '*', '*', '*') in self.slTable:
            realRoute = self.slTable[n, '*', '*', '*']

        # Case 12
        elif ('*', s, '*', '*') in self.slTable:
            realRoute = self.slTable['*', s, '*', '*']

        # Case 13
        elif ('*', '*', '*', c) in self.slTable:
            realRoute = self.slTable['*', '*', '*', c]

        # Case 14
        elif ('*', '*', l, '*') in self.slTable:
            realRoute = self.slTable['*', '*', l, '*']

        # Case 15
        elif ('*', '*', '*', '*') in self.slTable:
            realRoute = self.slTable['*', '*', '*', '*']

        result = []
        if realRoute is None:
            raise WIContentError('No routes have been found!')
            #return result

        for route in realRoute:
            # Check that I found a route
            if route is not None:
                result.append({'name': 'seedlink', 'url': route[0],
                               'params': [{'net': n, 'sta': s,
                                           'loc': l, 'cha': c,
                                           'start': '', 'end': ''}]})

                # result.append([route[0], n, s, l, c, None, None])
        return result

    def getRouteArc(self, n, s, l, c, startD=datetime.datetime(1980, 1, 1),
                    endD=datetime.datetime(datetime.date.today().year,
                                           datetime.date.today().month,
                                           datetime.date.today().day),
                    alternative=False):
        """Implement the following table lookup for the Arclink service

        01 NET STA CHA LOC # First try to match all.
        02 NET STA CHA --- # Then try to match all excluding location,
        03 NET STA --- LOC # ... and so on
        04 NET --- CHA LOC
        05 --- STA CHA LOC
        06 NET STA --- ---
        07 NET --- CHA ---
        08 NET --- --- LOC
        09 --- STA CHA ---
        09 --- STA --- LOC
        10 --- --- CHA LOC
        11 NET --- --- ---
        12 --- STA --- ---
        13 --- --- CHA ---
        14 --- --- --- LOC
        15 --- --- --- ---
"""

        realRoute = None

        # Case 1
        if (n, s, l, c) in self.routingTable:
            realRoute = self.routingTable[n, s, l, c]

        # Case 2
        elif (n, s, '*', c) in self.routingTable:
            realRoute = self.routingTable[n, s, '*', c]

        # Case 3
        elif (n, s, l, '*') in self.routingTable:
            realRoute = self.routingTable[n, s, l, '*']

        # Case 4
        elif (n, '*', l, c) in self.routingTable:
            realRoute = self.routingTable[n, '*', l, c]

        # Case 5
        elif ('*', s, l, c) in self.routingTable:
            realRoute = self.routingTable['*', s, l, c]

        # Case 6
        elif (n, s, '*', '*') in self.routingTable:
            realRoute = self.routingTable[n, s, '*', '*']

        # Case 7
        elif (n, '*', '*', c) in self.routingTable:
            realRoute = self.routingTable[n, '*', '*', c]

        # Case 8
        elif (n, '*', l, '*') in self.routingTable:
            realRoute = self.routingTable[n, '*', l, '*']

        # Case 9
        elif ('*', s, '*', c) in self.routingTable:
            realRoute = self.routingTable['*', s, '*', c]

        # Case 10
        elif ('*', '*', l, c) in self.routingTable:
            realRoute = self.routingTable['*', '*', l, c]

        # Case 11
        elif (n, '*', '*', '*') in self.routingTable:
            realRoute = self.routingTable[n, '*', '*', '*']

        # Case 12
        elif ('*', s, '*', '*') in self.routingTable:
            realRoute = self.routingTable['*', s, '*', '*']

        # Case 13
        elif ('*', '*', '*', c) in self.routingTable:
            realRoute = self.routingTable['*', '*', '*', c]

        # Case 14
        elif ('*', '*', l, '*') in self.routingTable:
            realRoute = self.routingTable['*', '*', l, '*']

        # Case 15
        elif ('*', '*', '*', '*') in self.routingTable:
            realRoute = self.routingTable['*', '*', '*', '*']

        result = []
        if realRoute is None:
            raise WIContentError('No routes have been found!')
            #raise Exception('No route in Arclink for stream %s.%s.%s.%s' %
            #                (n, s, l, c))

        bestPrio = None
        for route in realRoute:
            # Check that I found a route
            if route is not None:
                # Check if the timewindow is encompassed in the returned dates
                if ((endD < route[1] if endD is not None else False)
                        or (startD > route[2] if (None not in (startD,
                                                               route[2]))
                            else False)):
                    # If it is not, return None
                    #realRoute = None
                    continue
                else:
                    if alternative:
                        # FIXME Can we be sure that the alternative route will
                        # be always in another data center? We are just
                        # appending instead of MERGING data centers!
                        result.append({'name': 'arclink', 'url': route[0],
                                       'params': [{'net': n, 'sta': s,
                                                   'loc': l, 'cha': c,
                                                   'start': startD if startD is
                                                   not None else '',
                                                   'end': endD if endD is not
                                                   None else '',
                                                   'priority': route[3]}]})
                    elif ((bestPrio is None) or (route[3] < bestPrio)):
                        result = [{'name': 'arclink', 'url': route[0],
                                   'params': [{'net': n, 'sta': s,
                                               'loc': l, 'cha': c,
                                               'start': startD if startD is
                                               not None else '',
                                               'end': endD if endD is not
                                               None else '',
                                               'priority': route[3]}]}]
                        bestPrio = route[3]

        return result

    def updateMT(self):
        """Read the routes with highest priority for DS and store it in memory.

        All the routing information is read into a dictionary. Only the
        necessary attributes are stored. This relies on the idea
        that some other agent should update the routing file at
        a regular period of time.

        """

        # Just to shorten notation
        ptMT = self.masterTable

        # Parse the routing file
        # Traverse through the networks
        # get an iterable
        try:
            context = ET.iterparse(self.masterFile, events=("start", "end"))
        except IOError:
            msg = 'Error: masterTable.xml could not be opened.'
            print msg
            return

        # turn it into an iterator
        context = iter(context)

        # get the root element
        event, root = context.next()

        # Check that it is really an inventory
        if root.tag[-len('routing'):] != 'routing':
            msg = 'The file parsed seems not to be a routing file (XML).'
            print msg
            return

        # Extract the namespace from the root node
        namesp = root.tag[:-len('routing')]

        for event, route in context:
            # The tag of this node should be "route".
            # Now it is not being checked because
            # we need all the data, but if we need to filter, this
            # is the place.
            #
            if event == "end":
                if route.tag == namesp + 'route':

                    # Extract the location code
                    try:
                        locationCode = route.get('locationCode')
                        if len(locationCode) == 0:
                            locationCode = None
                    except:
                        locationCode = None

                    # Extract the network code
                    try:
                        networkCode = route.get('networkCode')
                        if len(networkCode) == 0:
                            networkCode = None
                    except:
                        networkCode = None

                    # Extract the station code
                    try:
                        stationCode = route.get('stationCode')
                        if len(stationCode) == 0:
                            stationCode = None
                    except:
                        stationCode = None

                    # Extract the stream code
                    try:
                        streamCode = route.get('streamCode')
                        if len(streamCode) == 0:
                            streamCode = None
                    except:
                        streamCode = None

                    # Traverse through the sources
                    #for arcl in route.findall(namesp + 'dataselect'):
                    for arcl in route:
                        service = arcl.tag.replace(namesp, '')
                        # Extract the address
                        try:
                            address = arcl.get('address')
                            if len(address) == 0:
                                continue
                        except:
                            continue

                        # Extract the priority
                        try:
                            prio = arcl.get('priority')
                        except:
                            prio = None

                        try:
                            startD = arcl.get('start')
                            if len(startD):
                                startParts = startD.replace('-', ' ')
                                startParts = startParts.replace('T', ' ')
                                startParts = startParts.replace(':', ' ')
                                startParts = startParts.replace('.', ' ')
                                startParts = startParts.replace('Z', '')
                                startParts = startParts.split()
                                startD = datetime.datetime(*map(int,
                                                                startParts))
                            else:
                                startD = None
                        except:
                            startD = None
                            print 'Error while converting START attribute.'

                        # Extract the end datetime
                        try:
                            endD = arcl.get('end')
                            if len(endD) == 0:
                                endD = None
                        except:
                            endD = None

                        try:
                            endD = arcl.get('end')
                            if len(endD):
                                endParts = endD.replace('-', ' ')
                                endParts = endParts.replace('T', ' ')
                                endParts = endParts.replace(':', ' ')
                                endParts = endParts.replace('.', ' ')
                                endParts = endParts.replace('Z', '').split()
                                endD = datetime.datetime(*map(int, endParts))
                            else:
                                endD = None
                        except:
                            endD = None
                            print 'Error while converting END attribute.'

                        # Append the network to the list of networks
                        if (networkCode, stationCode, locationCode,
                                streamCode) not in ptMT:
                            ptMT[networkCode, stationCode, locationCode,
                                 streamCode] = [RouteMT(address, startD, endD,
                                                        prio, service)]
                        else:
                            ptMT[networkCode, stationCode, locationCode,
                                 streamCode].append(RouteMT(address, startD,
                                                            endD, prio,
                                                            service))

                        arcl.clear()

                    route.clear()

                root.clear()

        # Order the routes by priority
        for keyDict in ptMT:
            ptMT[keyDict] = sorted(ptMT[keyDict])

    def update(self):
        """Read the routing file in XML format and store it in memory.

        All the routing information is read into a dictionary. Only the
        necessary attributes are stored. This relies on the idea
        that some other agent should update the routing file at
        a regular period of time.

        """

        # Just to shorten notation
        ptRT = self.routingTable
        ptSL = self.slTable
        ptST = self.stTable

        # Parse the routing file
        # Traverse through the networks
        # get an iterable
        try:
            print self.routingFile
            context = ET.iterparse(self.routingFile, events=("start", "end"))
        except IOError:
            msg = 'Error: %s could not be opened.' % self.routingFile
            raise Exception(msg)

        # turn it into an iterator
        context = iter(context)

        # get the root element
        event, root = context.next()

        # Check that it is really an inventory
        if root.tag[-len('routing'):] != 'routing':
            msg = 'The file parsed seems not to be an routing file (XML).'
            raise Exception(msg)

        # Extract the namespace from the root node
        namesp = root.tag[:-len('routing')]

        for event, route in context:
            # The tag of this node should be "route".
            # Now it is not being checked because
            # we need all the data, but if we need to filter, this
            # is the place.
            #
            if event == "end":
                if route.tag == namesp + 'route':

                    # Extract the location code
                    try:
                        locationCode = route.get('locationCode')
                        if len(locationCode) == 0:
                            locationCode = '*'
                    except:
                        locationCode = '*'

                    # Extract the network code
                    try:
                        networkCode = route.get('networkCode')
                        if len(networkCode) == 0:
                            networkCode = '*'
                    except:
                        networkCode = '*'

                    # Extract the station code
                    try:
                        stationCode = route.get('stationCode')
                        if len(stationCode) == 0:
                            stationCode = '*'
                    except:
                        stationCode = '*'

                    # Extract the stream code
                    try:
                        streamCode = route.get('streamCode')
                        if len(streamCode) == 0:
                            streamCode = '*'
                    except:
                        streamCode = '*'

                    # Traverse through the sources
                    for sl in route.findall(namesp + 'seedlink'):
                        # Extract the address
                        try:
                            address = sl.get('address')
                            if len(address) == 0:
                                continue
                        except:
                            continue

                        # Extract the priority
                        try:
                            priority = sl.get('priority')
                            if len(address) == 0:
                                priority = 99
                            else:
                                priority = int(priority)
                        except:
                            priority = 99

                        # Append the network to the list of networks
                        if (networkCode, stationCode, locationCode,
                                streamCode) not in ptSL:
                            ptSL[networkCode, stationCode, locationCode,
                                 streamCode] = [RouteSL(address, priority)]
                        else:
                            ptSL[networkCode, stationCode, locationCode,
                                 streamCode].append(RouteSL(address, priority))
                        sl.clear()

                    # Traverse through the sources
                    for arcl in route.findall(namesp + 'arclink'):
                        # Extract the address
                        try:
                            address = arcl.get('address')
                            if len(address) == 0:
                                continue
                        except:
                            continue

                        try:
                            startD = arcl.get('start')
                            if len(startD):
                                startParts = startD.replace('-', ' ')
                                startParts = startParts.replace('T', ' ')
                                startParts = startParts.replace(':', ' ')
                                startParts = startParts.replace('.', ' ')
                                startParts = startParts.replace('Z', '')
                                startParts = startParts.split()
                                startD = datetime.datetime(*map(int,
                                                                startParts))
                            else:
                                startD = None
                        except:
                            startD = None
                            print 'Error while converting START attribute.'

                        # Extract the end datetime
                        try:
                            endD = arcl.get('end')
                            if len(endD):
                                endParts = endD.replace('-', ' ')
                                endParts = endParts.replace('T', ' ')
                                endParts = endParts.replace(':', ' ')
                                endParts = endParts.replace('.', ' ')
                                endParts = endParts.replace('Z', '').split()
                                endD = datetime.datetime(*map(int, endParts))
                            else:
                                endD = None
                        except:
                            endD = None
                            print 'Error while converting END attribute.'

                        # Extract the priority
                        try:
                            priority = arcl.get('priority')
                            if len(address) == 0:
                                priority = 99
                            else:
                                priority = int(priority)
                        except:
                            priority = 99

                        # Append the network to the list of networks
                        if (networkCode, stationCode, locationCode,
                                streamCode) not in ptRT:
                            ptRT[networkCode, stationCode, locationCode,
                                 streamCode] = [Route(address, startD, endD,
                                                      priority)]
                        else:
                            ptRT[networkCode, stationCode, locationCode,
                                 streamCode].append(Route(address, startD,
                                                          endD, priority))
                        arcl.clear()

                    # Traverse through the sources
                    for statServ in route.findall(namesp + 'station'):
                        # Extract the address
                        try:
                            address = statServ.get('address')
                            if len(address) == 0:
                                continue
                        except:
                            continue

                        try:
                            startD = statServ.get('start')
                            if len(startD):
                                startParts = startD.replace('-', ' ')
                                startParts = startParts.replace('T', ' ')
                                startParts = startParts.replace(':', ' ')
                                startParts = startParts.replace('.', ' ')
                                startParts = startParts.replace('Z', '')
                                startParts = startParts.split()
                                startD = datetime.datetime(*map(int,
                                                                startParts))
                            else:
                                startD = None
                        except:
                            startD = None
                            print 'Error while converting START attribute.'

                        # Extract the end datetime
                        try:
                            endD = statServ.get('end')
                            if len(endD):
                                endParts = endD.replace('-', ' ')
                                endParts = endParts.replace('T', ' ')
                                endParts = endParts.replace(':', ' ')
                                endParts = endParts.replace('.', ' ')
                                endParts = endParts.replace('Z', '').split()
                                endD = datetime.datetime(*map(int, endParts))
                            else:
                                endD = None
                        except:
                            endD = None
                            print 'Error while converting END attribute.'

                        # Extract the priority
                        try:
                            priority = statServ.get('priority')
                            if len(address) == 0:
                                priority = 99
                            else:
                                priority = int(priority)
                        except:
                            priority = 99

                        # Append the network to the list of networks
                        if (networkCode, stationCode, locationCode,
                                streamCode) not in ptST:
                            ptST[networkCode, stationCode, locationCode,
                                 streamCode] = [Route(address, startD, endD,
                                                      priority)]
                        else:
                            ptST[networkCode, stationCode, locationCode,
                                 streamCode].append(Route(address, startD,
                                                          endD, priority))
                        statServ.clear()

                    route.clear()

                root.clear()

        # Order the routes by priority
        for keyDict in ptRT:
            ptRT[keyDict] = sorted(ptRT[keyDict])
            #ptRT[keyDict] = sorted(ptRT[keyDict], key=lambda route: route[3])

        # Order the routes by priority
        for keyDict in ptSL:
            ptSL[keyDict] = sorted(ptSL[keyDict])
            #ptSL[keyDict] = sorted(ptSL[keyDict], key=lambda route: route[1])

        # Order the routes by priority
        for keyDict in ptST:
            ptST[keyDict] = sorted(ptST[keyDict])
            #ptST[keyDict] = sorted(ptST[keyDict], key=lambda route: route[3])


def makeQueryGET(parameters):
    global routes

    # List all the accepted parameters
    allowedParams = ['net', 'network',
                     'sta', 'station',
                     'loc', 'location',
                     'cha', 'channel',
                     'start', 'starttime',
                     'end', 'endtime',
                     'service', 'format',
                     'alternative']

    for param in parameters:
        if param not in allowedParams:
            return 'Unknown parameter: %s' % param

    try:
        if 'network' in parameters:
            net = parameters['network'].value.upper()
        elif 'net' in parameters:
            net = parameters['net'].value.upper()
        else:
            net = '*'
    except:
        net = '*'

    try:
        if 'station' in parameters:
            sta = parameters['station'].value.upper()
        elif 'sta' in parameters:
            sta = parameters['sta'].value.upper()
        else:
            sta = '*'
    except:
        sta = '*'

    try:
        if 'location' in parameters:
            loc = parameters['location'].value.upper()
        elif 'loc' in parameters:
            loc = parameters['loc'].value.upper()
        else:
            loc = '*'
    except:
        loc = '*'

    try:
        if 'channel' in parameters:
            cha = parameters['channel'].value.upper()
        elif 'cha' in parameters:
            cha = parameters['cha'].value.upper()
        else:
            cha = '*'
    except:
        cha = '*'

    try:
        if 'starttime' in parameters:
            start = datetime.datetime.strptime(
                parameters['starttime'].value.upper(),
                '%Y-%m-%dT%H:%M:%S')
        elif 'start' in parameters:
            start = datetime.datetime.strptime(
                parameters['start'].value.upper(),
                '%Y-%m-%dT%H:%M:%S')
        else:
            start = None
    except:
        return 'Error while converting starttime parameter.'

    try:
        if 'endtime' in parameters:
            endt = datetime.datetime.strptime(
                parameters['endtime'].value.upper(),
                '%Y-%m-%dT%H:%M:%S')
        elif 'end' in parameters:
            endt = datetime.datetime.strptime(
                parameters['end'].value.upper(),
                '%Y-%m-%dT%H:%M:%S')
        else:
            endt = None
    except:
        return 'Error while converting endtime parameter.'

    try:
        if 'service' in parameters:
            ser = parameters['service'].value.lower()
        else:
            ser = 'dataselect'
    except:
        ser = 'dataselect'

    try:
        if 'alternative' in parameters:
            alt = True if parameters['alternative'].value.lower() == 'true'\
                else False
        else:
            alt = False
    except:
        alt = False

    route = routes.getRoute(net, sta, loc, cha, start, endt, ser, alt)

    if len(route) == 0:
        raise WIContentError('No routes have been found!')
    return route

# Add routing cache here, to be accessible to all modules
#here = os.path.dirname(__file__)
#routesFile = os.path.join(here, 'routing.xml')
#invFile = os.path.join(here, 'Arclink-inventory.xml')
#masterFile = os.path.join(here, 'masterTable.xml')
#routes = RoutingCache(routesFile, invFile, masterFile)

# This variable will be treated as GLOBAL by all the other functions
routes = None


def application(environ, start_response):
    """Main WSGI handler that processes client requests and calls
    the proper functions.

    Begun by Javier Quinteros <javier@gfz-potsdam.de>,
    GEOFON team, February 2014

    """

    global routes
    fname = environ['PATH_INFO']

    # Among others, this will filter wrong function names,
    # but also the favicon.ico request, for instance.
    if fname is None:
        raise WIClientError('Method name not recognized!')
        # return send_html_response(status, 'Error! ' + status, start_response)

    try:
        if environ['REQUEST_METHOD'] == 'GET':
            form = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ)
        elif environ['REQUEST_METHOD'] == 'POST':
            form = ''
            try:
                length = int(environ.get('CONTENT_LENGTH', '0'))
            except ValueError:
                length = 0
            # If there is a body to read
            if length != 0:
                form = environ['wsgi.input'].read(length)
            else:
                form = environ['wsgi.input'].read()

        else:
            raise Exception

    except ValueError, e:
        if str(e) == "Maximum content length exceeded":
            # Add some user-friendliness (this message triggers an alert
            # box on the client)
            return send_plain_response("400 Bad Request",
                                       "maximum request size exceeded",
                                       start_response)

        return send_plain_response("400 Bad Request", str(e), start_response)

    # Check whether the function called is implemented
    implementedFunctions = ['query', 'application.wadl', 'localconfig',
                            'version']

    if routes is None:
        # Add routing cache here, to be accessible to all modules
        here = os.path.dirname(__file__)
        routesFile = os.path.join(here, 'routing.xml')
        invFile = os.path.join(here, 'Arclink-inventory.xml')
        masterFile = os.path.join(here, 'masterTable.xml')
        routes = RoutingCache(routesFile, invFile, masterFile)

    fname = environ['PATH_INFO'].split('/')[-1]
    if fname not in implementedFunctions:
        return send_plain_response("400 Bad Request",
                                   'Function "%s" not implemented.' % fname,
                                   start_response)

    if fname == 'application.wadl':
        iterObj = ''
        here = os.path.dirname(__file__)
        appWadl = os.path.join(here, 'application.wadl')
        with open(appWadl, 'r') \
                as appFile:
            iterObj = appFile.read()
            status = '200 OK'
            return send_xml_response(status, iterObj, start_response)

    elif fname == 'query':
        makeQuery = globals()['makeQuery%s' % environ['REQUEST_METHOD']]
        try:
            iterObj = makeQuery(form)
        except WIError as w:
            return send_plain_response(w.status, w.body, start_response)

    elif fname == 'localconfig':
        return send_xml_response('200 OK', routes.localConfig(),
                                 start_response)

    if isinstance(iterObj, basestring):
        status = '200 OK'
        return send_plain_response(status, iterObj, start_response)

    if (isinstance(iterObj, dict) or isinstance(iterObj, list) or
            isinstance(iterObj, tuple)):
        status = '200 OK'
        if 'format' in form and form['format'].value.lower() == 'json':
            iterObj = json.dumps(iterObj, default=datetime.datetime.isoformat)
            return send_plain_response(status, iterObj, start_response)
        elif 'format' in form and form['format'].value.lower() == 'get':
            result = []
            for datacenter in iterObj:
                for item in datacenter['params']:
                    result.append(datacenter['url'] + '?' +
                                  '&'.join([k + '=' + item[k] for k in
                                            item if item[k] not in ('', '*')]))
            result = '\n'.join(result)
            return send_plain_response(status, result, start_response)
        elif 'format' in form and form['format'].value.lower() == 'post':
            result = []
            for datacenter in iterObj:
                result.append(datacenter['url'])
                for item in datacenter['params']:
                    item['loc'] = item['loc'] if len(item['loc']) else '--'
                    result.append(item['net'] + ' ' + item['sta'] + ' ' +
                                  item['loc'] + ' ' + item['cha'] + ' ' +
                                  item['start'] + ' ' + item['end'])
                result.append('')
            result = '\n'.join(result)
            return send_plain_response(status, result, start_response)
        else:
            iterObj2 = ET.tostring(ConvertDictToXml(iterObj))
            return send_xml_response(status, iterObj2, start_response)

    status = '200 OK'
    body = "\n".join(iterObj)
    return send_plain_response(status, body, start_response)


def main():
    routes = RoutingCache("./routing.xml", "./Arclink-inventory.xml",
                          "./masterTable.xml")
    print len(routes.routingTable)


if __name__ == "__main__":
    main()
