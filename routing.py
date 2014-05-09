#!/usr/bin/env python
#
# FDSN-WS Dataselect prototype
#
# (c) 2014 Javier Quinteros, GEOFON team
# <javier@gfz-potsdam.de>
#
# ----------------------------------------------------------------------

"""Routing information management for an EIDA FDSN-WS (Dataselect)

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


import datetime
import xml.etree.cElementTree as ET


class RoutingException(Exception):
    pass


class RoutingCache(object):
    """Encapsulate and manage routing information of networks,
    stations, locations and streams read from an Arclink XML file.

    Begun by Javier Quinteros <javier@gfz-potsdam.de>, GEOFON team, June 2014

    """

    def __init__(self, routingFile):
        # Arclink routing file in XML format
        self.routingFile = routingFile

        # Dictionary with all the routes
        self.routingTable = dict()

        # Create/load the cache the first time that we start
        self.update()

    def getRoute(self, n, s, l, c, startD=datetime.datetime(1980, 1, 1),
                 endD=datetime.datetime.now(), service='dataselect'):
        if service == 'arclink':
            return self.getRouteArc(n, s, l, c, startD, endD)
        elif service == 'dataselect':
            return self.getRouteDS(n, s, l, c, startD, endD)

        # Through an exception if there is an error
        raise RoutingException('Unknown service: %s' % service)

    def getRouteDS(self, n, s, l, c, startD=datetime.datetime.now(),
                   endD=datetime.datetime.now()):
        """Use the table lookup from Arclink to route the Dataselect service
"""

        realRoute = self.getRouteArc(n, s, l, c, startD, endD)

        # Try to identify the hosting institution
        host = realRoute.split(':')[0]

        if host.endswith('gfz-potsdam.de'):
            result = 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query'
        elif host.endswith('knmi.nl'):
            result = 'http://www.orfeus-eu.org/fdsnws/dataselect/1/query'
        elif host.endswith('ethz.ch'):
            result = 'http://eida.ethz.ch/fdsnws/dataselect/1/query'
        elif host.endswith('resif.fr'):
            result = 'http://ws.resif.fr/fdsnws/dataselect/1/query'
        else:
            raise RoutingException('No Dataselect WS registered for %s' % host)

        return result

    def getRouteArc(self, n, s, l, c, startD=datetime.datetime.now(),
                    endD=datetime.datetime.now()):
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
        elif (n, s, None, c) in self.routingTable:
            realRoute = self.routingTable[n, s, None, c]

        # Case 3
        elif (n, s, l, None) in self.routingTable:
            realRoute = self.routingTable[n, s, l, None]

        # Case 4
        elif (n, None, l, c) in self.routingTable:
            realRoute = self.routingTable[n, None, l, c]

        # Case 5
        elif (None, s, l, c) in self.routingTable:
            realRoute = self.routingTable[None, s, l, c]

        # Case 6
        elif (n, s, None, None) in self.routingTable:
            realRoute = self.routingTable[n, s, None, None]

        # Case 7
        elif (n, None, None, c) in self.routingTable:
            realRoute = self.routingTable[n, None, None, c]

        # Case 8
        elif (n, None, l, None) in self.routingTable:
            realRoute = self.routingTable[n, None, l, None]

        # Case 9
        elif (None, s, None, c) in self.routingTable:
            realRoute = self.routingTable[None, s, None, c]

        # Case 10
        elif (None, None, l, c) in self.routingTable:
            realRoute = self.routingTable[None, None, l, c]

        # Case 11
        elif (n, None, None, None) in self.routingTable:
            realRoute = self.routingTable[n, None, None, None]

        # Case 12
        elif (None, s, None, None) in self.routingTable:
            realRoute = self.routingTable[None, s, None, None]

        # Case 13
        elif (None, None, None, c) in self.routingTable:
            realRoute = self.routingTable[None, None, None, c]

        # Case 14
        elif (None, None, l, None) in self.routingTable:
            realRoute = self.routingTable[None, None, l, None]

        # Case 15
        elif (None, None, None, None) in self.routingTable:
            realRoute = self.routingTable[None, None, None, None]

        # Check if the timewindow is encompassed in the returned dates
        if ((endD < realRoute[1]) or (startD > realRoute[2])):
            # If it is not, return None
            return None

        return realRoute[0]

    def update(self):
        """Read the routing file in XML format and store it in memory.

        All the routing information is read into a dictionary. Only the
        necessary attributes are stored. This relies on the idea
        that some other agent should update the routing file at
        a regular period of time.

        """

        # Just to shorten notation
        ptRT = self.routingTable

        # Parse the routing file
        # Traverse through the networks
        # get an iterable
        try:
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
                    for arcl in route.findall(namesp + 'arclink'):
                        # Extract the address
                        try:
                            address = arcl.get('address')
                            if len(address) == 0:
                                continue
                        except:
                            continue

                        # Extract the start datetime
                        try:
                            startD = arcl.get('start')
                            if len(startD) == 0:
                                startD = None
                        except:
                            startD = None

                        # Extract the end datetime
                        try:
                            endD = arcl.get('end')
                            if len(endD) == 0:
                                endD = None
                        except:
                            endD = None

                        # Append the network to the list of networks
                        ptRT[networkCode, stationCode, locationCode,
                             streamCode] = (address, startD, endD)

                        arcl.clear()

                    route.clear()

                root.clear()


def main():
    routes = RoutingCache("./routing.xml")
    print len(routes.routingTable)


if __name__ == "__main__":
    main()
