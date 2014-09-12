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
import xml.etree.cElementTree as ET
from inventorycache import InventoryCache
from wsgicomm import *


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

        # Create/load the cache the first time that we start
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

    def __arc2DS(self, route):
        """Map from an Arclink address to a Dataselect one."""

        gfz = 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query'
        odc = 'http://www.orfeus-eu.org/fdsnws/dataselect/1/query'
        eth = 'http://eida.ethz.ch/fdsnws/dataselect/1/query'
        resif = 'http://ws.resif.fr/fdsnws/dataselect/1/query'
        ingv = 'http://webservices.rm.ingv.it/fdsnws/dataselect/1/query'
        bgr = 'http://eida.bgr.de/fdsnws/dataselect/1/query'
        lmu = 'http://st35:8080/fdsnws/dataselect/1/query'
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

    def getRoute(self, n='*', s='*', l='*', c='*',
                 startD=datetime.datetime(1980, 1, 1),
                 endD=datetime.datetime(datetime.date.today().year,
                                        datetime.date.today().month,
                                        datetime.date.today().day),
                 service='dataselect'):
        """getRoute receives a stream and a timewindow and returns a list.
        The list has the following format:
            [[URL_1, net_1, sta_1, loc_1, cha_1, tfrom_1, tto_1],
            ...
             [URL_n, net_n, sta_n, loc_n, cha_n, tfrom_n, tto_n]]
        """

        if service == 'arclink':
            return self.getRouteArc(n, s, l, c, startD, endD)
        elif service == 'dataselect':
            return self.getRouteDS(n, s, l, c, startD, endD)
        elif service == 'seedlink':
            return self.getRouteSL(n, s, l, c)

        # Through an exception if there is an error
        raise RoutingException('Unknown service: %s' % service)

    def getRouteDS(self, n='*', s='*', l='*', c='*',
                   startD=datetime.datetime(1980, 1, 1),
                   endD=datetime.datetime(datetime.date.today().year,
                                          datetime.date.today().month,
                                          datetime.date.today().day)):
        """Use the table lookup from Arclink to route the Dataselect service
"""

        result = []

        masterRoute = self.getRouteMaster(n)
        if masterRoute is not None:
            return ['http://' + masterRoute, n, s, l, c, startD, endD]

        # Check if there are wildcards!
        if (('*' in n + s + l + c) or ('?' in n + s + l + c)):
            # Filter first by the attributes without wildcards

            # Check for the timewindow
            subs = self.routingTable.keys()

            if ((s is not None) and ('*' not in s) and ('?' not in s)):
                subs = [k for k in subs if (k[1] is None or k[1] == '*' or
                                            k[1] == s)]

            if ((n is not None) and ('*' not in n) and ('?' not in n)):
                subs = [k for k in subs if (k[0] is None or k[0] == '*' or
                                            k[0] == n)]

            if ((c is not None) and ('*' not in c) and ('?' not in c)):
                subs = [k for k in subs if (k[3] is None or k[3] == '*' or
                                            k[3] == c)]

            if ((l is not None) and ('*' not in l) and ('?' not in l)):
                subs = [k for k in subs if (k[2] is None or k[2] == '*' or
                                            k[2] == l)]

            # Filter then by the attributes WITH wildcards
            if ((s is None) or ('*' in s) or ('?' in s)):
                subs = [k for k in subs if (k[1] is None or k[1] == '*' or
                                            fnmatch.fnmatch(k[1], s))]

            if ((n is None) or ('*' in n) or ('?' in n)):
                subs = [k for k in subs if (k[0] is None or k[0] == '*' or
                                            fnmatch.fnmatch(k[0], n))]

            if ((c is None) or ('*' in c) or ('?' in c)):
                subs = [k for k in subs if (k[3] is None or k[3] == '*' or
                                            fnmatch.fnmatch(k[3], c))]

            if ((l is None) or ('*' in l) or ('?' in l)):
                subs = [k for k in subs if (k[2] is None or k[2] == '*' or
                                            fnmatch.fnmatch(k[2], l))]

            resSet = set()
            for k in subs:
                # ONLY the first component of the tuple!!!
                # print k, self.routingTable[k]
                for rou in self.routingTable[k]:
                    # Check that the timewindow is OK
                    if (((rou[2] is None) or (startD < rou[2])) and
                            (endD > rou[1])):
                        resSet.add(self.__arc2DS(rou[0]))

            # Check the coherency of the routes to set the return code
            if len(resSet) == 0:
                raise Exception()
            elif len(resSet) == 1:
                return [resSet.pop(), n, s, l, c, startD, endD]
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

                    # The break from 5 lines above jumps until this line in
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
                            finalset.append(rExp)

                # In finalset I have all the streams (including expanded and
                # the ones with wildcards), that I need to request.
                # Now I need the URLs
                result = list()
                for st in finalset:
                    url2Add = [self.__arc2DS(self.getRouteArc(st[0], st[1],
                                                              st[2], st[3],
                                                              startD,
                                                              endD)[0]),
                               st[0], st[1], st[2], st[3], startD, endD]
                    result.append(url2Add)

                return result

            raise Exception('This point should have nevere been reached! ;-)')

        # If there are NO wildcards
        realRoute = self.getRouteArc(n, s, l, c, startD, endD)
        #if not len(realRoute):
        #    return [iris]

        for route in realRoute:
            # Translate an Arclink address to a Dataselect one
            host = self.__arc2DS(route)
            if (host is not None) and (host not in result):
                result.append(host)

        # The route return by Arclink is unique. The others are alternative
        # routes.
        retCode = 0
        return (retCode, result)

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

    def getRouteMaster(self, n, startD=datetime.datetime(1980, 1, 1),
                       endD=datetime.datetime(datetime.date.today().year,
                                              datetime.date.today().month,
                                              datetime.date.today().day)):
        """Implement the following table lookup for the Master Table

        11 NET --- --- ---
"""

        realRoute = None

        # Case 11
        if (n, None, None, None) in self.masterTable:
            realRoute = self.masterTable[n, None, None, None]

        # print "Search %s in masterTable. Found %s" % (n, realRoute)
        # Check that I found a route
        if realRoute is not None:
            # Check if the timewindow is encompassed in the returned dates
            if ((endD < realRoute[1]) or (startD > realRoute[2] if realRoute[2]
                                          is not None else False)):
                # If it is not, return None
                realRoute = None
            else:
                realRoute = realRoute[0]

        return realRoute

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
            return result

        for route in realRoute:
            # Check that I found a route
            if route is not None:
                result.append([route[0], n, s, l, c, None, None])

        #return realRoute
        return result

    def getRouteArc(self, n, s, l, c, startD=datetime.datetime(1980, 1, 1),
                    endD=datetime.datetime(datetime.date.today().year,
                                           datetime.date.today().month,
                                           datetime.date.today().day)):
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
            raise Exception('No route in Arclink for stream %s.%s.%s.%s' %
                            (n, s, l, c))

        for route in realRoute:
            # Check that I found a route
            if route is not None:
                # Check if the timewindow is encompassed in the returned dates
                if ((endD < route[1]) or (startD > route[2] if route[2]
                                          is not None else False)):
                    # If it is not, return None
                    #realRoute = None
                    continue
                else:
                    result.append([route[0], n, s, l, c, startD, endD])

        #return realRoute
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
                    for arcl in route.findall(namesp + 'dataselect'):
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
                        ptMT[networkCode, stationCode, locationCode,
                             streamCode] = (address, startD, endD)

                        arcl.clear()

                    route.clear()

                root.clear()

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

        # Parse the routing file
        # Traverse through the networks
        # get an iterable
        try:
            print self.routingFile
            context = ET.iterparse(self.routingFile, events=("start", "end"))
        except IOError:
            msg = 'Error: routing.xml could not be opened.'
            print msg
            return

        # turn it into an iterator
        context = iter(context)

        # get the root element
        event, root = context.next()

        # Check that it is really an inventory
        if root.tag[-len('routing'):] != 'routing':
            msg = 'The file parsed seems not to be an routing file (XML).'
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
                            priority = arcl.get('priority')
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
                                 streamCode] = [(address, priority)]
                        else:
                            ptSL[networkCode, stationCode, locationCode,
                                 streamCode].append((address, priority))
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
                                 streamCode] = [(address, startD, endD,
                                                 priority)]
                        else:
                            ptRT[networkCode, stationCode, locationCode,
                                 streamCode].append((address, startD, endD,
                                                     priority))
                        arcl.clear()

                    route.clear()

                root.clear()

        # Order the routes by priority
        for keyDict in ptRT:
            ptRT[keyDict] = sorted(ptRT[keyDict], key=lambda route: route[3])

        # Order the routes by priority
        for keyDict in ptSL:
            ptSL[keyDict] = sorted(ptSL[keyDict], key=lambda route: route[1])


def makeQueryGET(parameters):
    # List all the accepted parameters
    allowedParams = ['net', 'network',
                     'sta', 'station',
                     'loc', 'location',
                     'cha', 'channel',
                     'start', 'starttime',
                     'end', 'endtime',
                     'service']

    for param in parameters:
        if param not in allowedParams:
            return 'Unknown parameter: %s' % param

    try:
        if 'network' in parameters:
            net = parameters['network'].value
        elif 'net' in parameters:
            net = parameters['net'].value
        else:
            net = '*'
    except:
        net = '*'

    try:
        if 'station' in parameters:
            sta = parameters['station'].value
        elif 'sta' in parameters:
            sta = parameters['sta'].value
        else:
            sta = '*'
    except:
        sta = '*'

    try:
        if 'location' in parameters:
            loc = parameters['location'].value
        elif 'loc' in parameters:
            loc = parameters['loc'].value
        else:
            loc = '*'
    except:
        loc = '*'

    try:
        if 'channel' in parameters:
            cha = parameters['channel'].value
        elif 'cha' in parameters:
            cha = parameters['cha'].value
        else:
            cha = '*'
    except:
        cha = '*'

    try:
        if 'starttime' in parameters:
            start = datetime.datetime.strptime(
                parameters['starttime'].value,
                '%Y-%m-%dT%H:%M:%S')
        elif 'start' in parameters:
            start = datetime.datetime.strptime(
                parameters['start'].value,
                '%Y-%m-%dT%H:%M:%S')
        else:
            start = datetime.datetime(1980, 1, 1)
    except:
        return 'Error while converting starttime parameter.'

    try:
        if 'endtime' in parameters:
            endt = datetime.datetime.strptime(
                parameters['endtime'].value,
                '%Y-%m-%dT%H:%M:%S')
        elif 'end' in parameters:
            endt = datetime.datetime.strptime(
                parameters['end'].value,
                '%Y-%m-%dT%H:%M:%S')
        else:
            d = datetime.date.today() + datetime.timedelta(days=1)
            endt = datetime.datetime(d.year, d.month, d.day)
    except:
        return 'Error while converting endtime parameter.'

    try:
        if 'service' in parameters:
            ser = parameters['service'].value
        else:
            ser = 'dataselect'
    except:
        ser = 'dataselect'

    route = routes.getRoute(net, sta, loc, cha, start, endt, ser)

    return route

# Add routing cache here, to be accessible to all modules
here = os.path.dirname(__file__)
routesFile = os.path.join(here, 'routing.xml')
invFile = os.path.join(here, 'Arclink-inventory.xml')
masterFile = os.path.join(here, 'masterTable.xml')
routes = RoutingCache(routesFile, invFile, masterFile)


def application(environ, start_response):
    """Main WSGI handler that processes client requests and calls
    the proper functions.

    Begun by Javier Quinteros <javier@gfz-potsdam.de>,
    GEOFON team, February 2014

    """

    fname = environ['PATH_INFO']

    # Among others, this will filter wrong function names,
    # but also the favicon.ico request, for instance.
    if fname is None:
        return send_html_response(status, 'Error! ' + status, start_response)

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
    implementedFunctions = ['query', 'application.wadl']

    fname = environ['PATH_INFO'].split('/')[-1]
    if fname not in implementedFunctions:
        return send_plain_response("400 Bad Request",
                                   'Function "%s" not implemented.' % fname,
                                   start_response)

    if fname == 'application.wadl':
        iterObj = ''
        with open('/var/www/fdsnws/routing/application.wadl', 'r') \
                as appFile:
            iterObj = appFile.read()
            status = '200 OK'
            return send_xml_response(status, iterObj, start_response)

    elif fname == 'query':
        makeQuery = globals()['makeQuery%s' % environ['REQUEST_METHOD']]
        iterObj = makeQuery(form)

    if isinstance(iterObj, basestring):
        status = '200 OK'
        return send_plain_response(status, iterObj, start_response)

    if isinstance(iterObj, list) or isinstance(iterObj, tuple):
        status = '200 OK'
        iterObj = json.dumps(iterObj, default=datetime.datetime.isoformat)
        return send_plain_response(status, iterObj, start_response)

    status = '200 OK'
    body = "\n".join(iterObj)
    return send_plain_response(status, body, start_response)


def main():
    routes = RoutingCache("./routing.xml", "./masterTable.xml")
    print len(routes.routingTable)


if __name__ == "__main__":
    main()
