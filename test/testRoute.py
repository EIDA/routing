#!/usr/bin/env python3

"""Tests to check that Routing Service classes are working

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

   :Copyright:
       2014-2020 Javier Quinteros, Deutsches GFZ Potsdam <javier@gfz-potsdam.de>
   :License:
       GPLv3
   :Platform:
       Linux

.. moduleauthor:: Javier Quinteros <javier@gfz-potsdam.de>, GEOFON, GFZ Potsdam
"""

import sys
import os
import datetime
import urllib.request as ul
import unittest

here = os.path.dirname(__file__)
sys.path.append(os.path.join(here, '..'))

from routeutils.unittestTools import WITestRunner
from routeutils.utils import RoutingCache
from routeutils.utils import RequestMerge
from routeutils.utils import FDSNRules
from routeutils.utils import Stream
from routeutils.utils import TW
from routeutils.utils import geoRectangle
from routeutils.utils import RoutingException


class RouteCacheTests(unittest.TestCase):
    """Test the functionality of routing.py

    """

    @classmethod
    def setUp(cls):
        "Setting up test"
        if hasattr(cls, 'rc'):
            return
        cls.rc = RoutingCache('../data/routing.xml.sample')

    def testDS_GE_FDSN_output(self):
        """Dataselect GE.*.*.* start=2010 format=fdsn"""

        expURL = 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/'
        startD = datetime.datetime(2010, 1, 1)
        result = self.rc.getRoute(Stream('GE', '*', '*', '*'), TW(startD, None))
        self.assertIsInstance(result, RequestMerge,
                              'A RequestMerge object was expected!')

        fdsnResult = FDSNRules(result)
        self.assertEqual(len(fdsnResult['datacenters']), 1,
                         'Wrong number of data centers for GE.*.*.*!')
        tsr = fdsnResult['datacenters'][0]['repositories'][0]['timeseriesRouting']
        self.assertEqual(len(tsr), 1,
                         'Wrong number of rules for GE.*.*.*!')
        self.assertEqual(tsr[0]['network'], 'GE',
                         'Wrong network code')
        self.assertEqual(tsr[0]['services'][0]['url'], expURL,
                         'Wrong URL for GE.*.*.*')
        self.assertEqual(tsr[0]['services'][0]['name'], 'fdsnws-dataselect',
                         'Wrong service name!')

    def testDS_XXX(self):
        """Non-existing network XXX"""

        try:
            result = self.rc.getRoute(Stream('XXX', '*', '*', '*'), TW(None, None))
        except RoutingException:
            return

        self.assertTrue(False, 'A RoutingException was expected!')

    def test_wrong_datetime(self):
        """Swap start and end time."""

        d1 = datetime.datetime(2004, 1, 1)
        d2 = d1 - datetime.timedelta(days=1)

        try:
            result = self.rc.getRoute(Stream('GE', '*', '*', '*'), TW(d1, d2))
        except RoutingException:
            return

        self.assertTrue(False, 'A RoutingException was expected!')

    def testDS_ZE(self):
        """Dataselect ZE.*.*.*"""

        expURL = 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query'
        result = self.rc.getRoute(Stream('ZE', '*', '*', '*'), TW(None, None))
        self.assertIsInstance(result, RequestMerge,
                              'A RequestMerge object was expected!')
        self.assertEqual(len(result), 1,
                         'Wrong number of data centers for GE.*.*.*!')
        self.assertEqual(len(result[0]['params']), 4,
                         '4 epochs are expected from the ZE network')
        self.assertEqual(result[0]['name'], 'dataselect',
                         'Wrong service name!')

    def test2services_GE_DS_ST(self):
        """Dataselect AND Station GE.*.*.*"""

        expURL_DS = 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query'
        expURL_ST = 'http://geofon.gfz-potsdam.de/fdsnws/station/1/query'
        result = self.rc.getRoute(Stream('GE', '*', '*', '*'), TW(None, None), service='dataselect,station')
        self.assertIsInstance(result, RequestMerge,
                              'A RequestMerge object was expected!')
        self.assertEqual(len(result), 2,
                         'Wrong number of data centers for GE.*.*.*!')
        self.assertIn(expURL_DS, [result[0]['url'], result[1]['url']],
                      'Wrong URL for GE.*.*.*')
        self.assertIn(expURL_ST, [result[0]['url'], result[1]['url']],
                      'Wrong URL for GE.*.*.*')
        self.assertIn('dataselect', [result[0]['name'], result[1]['name']],
                      'Wrong service name!')
        self.assertIn('station', [result[0]['name'], result[1]['name']],
                      'Wrong service name!')

    def test2services_GE_DS_ST_FDSN(self):
        """Dataselect AND Station GE.*.*.* in FDSN format"""

        expURL_DS = 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/'
        expURL_ST = 'http://geofon.gfz-potsdam.de/fdsnws/station/1/'
        result = self.rc.getRoute(Stream('GE', '*', '*', '*'), TW(None, None), service='dataselect,station')
        fdsnresult = FDSNRules(result)
        self.assertIsInstance(fdsnresult, FDSNRules,
                              'A FDSNRules object was expected!')
        self.assertEqual(len(fdsnresult['datacenters'][0]['repositories'][0]['timeseriesRouting'][0]['services']), 2,
                         'Wrong number of services for GE.*.*.*!')
        self.assertIn(expURL_DS, [fdsnresult['datacenters'][0]['repositories'][0]['timeseriesRouting'][0]['services'][0]['url'],
                                  fdsnresult['datacenters'][0]['repositories'][0]['timeseriesRouting'][0]['services'][1]['url']],
                      'Dataselect URL not found for GE.*.*.*')
        self.assertIn(expURL_ST, [fdsnresult['datacenters'][0]['repositories'][0]['timeseriesRouting'][0]['services'][0]['url'],
                                  fdsnresult['datacenters'][0]['repositories'][0]['timeseriesRouting'][0]['services'][1]['url']],
                      'StationWS URL not found for GE.*.*.*')
        self.assertIn('fdsnws-dataselect', [fdsnresult['datacenters'][0]['repositories'][0]['timeseriesRouting'][0]['services'][0]['name'],
                                            fdsnresult['datacenters'][0]['repositories'][0]['timeseriesRouting'][0]['services'][1]['name']],
                      'Dataselect name not found for GE.*.*.*')
        self.assertIn('fdsnws-station', [fdsnresult['datacenters'][0]['repositories'][0]['timeseriesRouting'][0]['services'][0]['name'],
                                         fdsnresult['datacenters'][0]['repositories'][0]['timeseriesRouting'][0]['services'][1]['name']],
                      'StationWS name not found for GE.*.*.*')

    def test2services_GE_DS_ST_WF(self):
        """Dataselect AND Station AND WFCatalog GE.*.*.*"""

        expURL_WF = 'http://geofon.gfz-potsdam.de/eidaws/wfcatalog/1/query'
        expURL_DS = 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query'
        expURL_ST = 'http://geofon.gfz-potsdam.de/fdsnws/station/1/query'
        result = self.rc.getRoute(Stream('GE', '*', '*', '*'), TW(None, None), service='dataselect,station,wfcatalog')
        self.assertIsInstance(result, RequestMerge,
                              'A RequestMerge object was expected!')
        self.assertEqual(len(result), 3,
                         'Wrong number of data centers for GE.*.*.*!')
        self.assertIn(expURL_DS, [result[0]['url'], result[1]['url'], result[2]['url']],
                      'Wrong URL for GE.*.*.*')
        self.assertIn(expURL_ST, [result[0]['url'], result[1]['url'], result[2]['url']],
                      'Wrong URL for GE.*.*.*')
        self.assertIn(expURL_WF, [result[0]['url'], result[1]['url'], result[2]['url']],
                      'Wrong URL for GE.*.*.*')
        self.assertIn('dataselect', [result[0]['name'], result[1]['name'], result[2]['name']],
                      'Wrong service name!')
        self.assertIn('station', [result[0]['name'], result[1]['name'], result[2]['name']],
                      'Wrong service name!')
        self.assertIn('wfcatalog', [result[0]['name'], result[1]['name'], result[2]['name']],
                      'Wrong service name!')

    def test2services_GE_DS_ST_WF_FDSN(self):
        """Dataselect AND Station AND WFCatalog GE.*.*.* in FDSN format"""

        result = self.rc.getRoute(Stream('GE', '*', '*', '*'), TW(None, None), service='dataselect,wfcatalog,station')
        fdsnresult = FDSNRules(result)
        self.assertIsInstance(fdsnresult, FDSNRules,
                              'A FDSNRules object was expected!')
        self.assertEqual(len(fdsnresult['datacenters'][0]['repositories'][0]['timeseriesRouting'][0]['services']), 0,
                         'Wrong number of services for GE.*.*.*! An empty list is expected.')

    def test2services_GE_ST_WF(self):
        """Station AND WFCatalog GE.*.*.*"""

        expURL_WF = 'http://geofon.gfz-potsdam.de/eidaws/wfcatalog/1/query'
        expURL_ST = 'http://geofon.gfz-potsdam.de/fdsnws/station/1/query'
        result = self.rc.getRoute(Stream('GE', '*', '*', '*'), TW(None, None), service='station,wfcatalog')
        self.assertIsInstance(result, RequestMerge,
                              'A RequestMerge object was expected!')
        self.assertEqual(len(result), 2,
                         'Wrong number of data centers for GE.*.*.*!')
        self.assertIn(expURL_ST, [result[0]['url'], result[1]['url']],
                      'Wrong URL for GE.*.*.*')
        self.assertIn(expURL_WF, [result[0]['url'], result[1]['url']],
                      'Wrong URL for GE.*.*.*')
        self.assertIn('station', [result[0]['name'], result[1]['name']],
                      'Wrong service name!')
        self.assertIn('wfcatalog', [result[0]['name'], result[1]['name']],
                      'Wrong service name!')

    def test2services_GE_ST_WF_FDSN(self):
        """Station AND WFCatalog GE.*.*.* in FDSN format"""

        expURL_WF = 'http://geofon.gfz-potsdam.de/eidaws/wfcatalog/1/'
        expURL_ST = 'http://geofon.gfz-potsdam.de/fdsnws/station/1/'
        result = self.rc.getRoute(Stream('GE', '*', '*', '*'), TW(None, None), service='wfcatalog,station')
        fdsnresult = FDSNRules(result)
        self.assertIsInstance(fdsnresult, FDSNRules,
                              'A FDSNRules object was expected!')
        self.assertEqual(len(fdsnresult['datacenters'][0]['repositories'][0]['timeseriesRouting'][0]['services']), 2,
                         'Wrong number of services for GE.*.*.*!')
        self.assertIn(expURL_WF, [fdsnresult['datacenters'][0]['repositories'][0]['timeseriesRouting'][0]['services'][0]['url'],
                                  fdsnresult['datacenters'][0]['repositories'][0]['timeseriesRouting'][0]['services'][1]['url']],
                      'WFCatalog URL not found for GE.*.*.*')
        self.assertIn(expURL_ST, [fdsnresult['datacenters'][0]['repositories'][0]['timeseriesRouting'][0]['services'][0]['url'],
                                  fdsnresult['datacenters'][0]['repositories'][0]['timeseriesRouting'][0]['services'][1]['url']],
                      'StationWS URL not found for GE.*.*.*')
        self.assertIn('eidaws-wfcatalog', [fdsnresult['datacenters'][0]['repositories'][0]['timeseriesRouting'][0]['services'][0]['name'],
                                           fdsnresult['datacenters'][0]['repositories'][0]['timeseriesRouting'][0]['services'][1]['name']],
                      'WFCatalog name not found for GE.*.*.*')
        self.assertIn('fdsnws-station', [fdsnresult['datacenters'][0]['repositories'][0]['timeseriesRouting'][0]['services'][0]['name'],
                                         fdsnresult['datacenters'][0]['repositories'][0]['timeseriesRouting'][0]['services'][1]['name']],
                      'StationWS name not found for GE.*.*.*')

    def testDS_GE(self):
        """Dataselect GE.*.*.*"""

        expURL = 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query'
        result = self.rc.getRoute(Stream('GE', '*', '*', '*'), TW(None, None))
        self.assertIsInstance(result, RequestMerge,
                              'A RequestMerge object was expected!')
        self.assertEqual(len(result), 1,
                         'Wrong number of data centers for GE.*.*.*!')
        self.assertEqual(result[0]['url'], expURL,
                         'Wrong URL for GE.*.*.*')
        self.assertEqual(result[0]['name'], 'dataselect',
                         'Wrong service name!')

    def test_geolocation(self):
        """Station GE.*.*.* with latitude between -10 and 10"""

        expURL = 'http://geofon.gfz-potsdam.de/fdsnws/station/1/query'
        result = self.rc.getRoute(Stream('GE', '*', '*', '*'), TW(None, None),
                                  'station',
                                  geoLoc=geoRectangle(-10, 10, -180, 180))
        self.assertIsInstance(result, RequestMerge,
                              'A RequestMerge object was expected!')
        self.assertEqual(len(result), 1,
                         'Wrong number of data centers for GE.*.*.*!')
        self.assertEqual(result[0]['url'], expURL,
                         'Wrong URL for GE.*.*.*')
        self.assertEqual(result[0]['name'], 'station',
                         'Wrong service name!')

        queryparams = '?net={net}&sta={sta}&loc={loc}&cha={cha}&minlat=-10&maxlat=10&format=text'
        for st in result[0]['params']:
            req = ul.Request(expURL + queryparams.format_map(st))
            try:
                u = ul.urlopen(req)
                buffer = u.read().decode('utf-8')
            except Exception:
                raise Exception('Error retrieving GE stations with latitude between -10 and 10')

            for line in buffer.splitlines():
                if line.startswith('#'):
                    continue

                self.assertGreaterEqual(float(line.split('|')[2]), -10.0,
                                        'Latitude smaller than -10.0!')
                self.assertLessEqual(float(line.split('|')[2]), 10.0,
                                     'Latitude bigger than 10.0!')
                break


    def testDS_GE_noEnd(self):
        """Dataselect GE.*.*.* start=2010"""

        expURL = 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query'
        startD = datetime.datetime(2010, 1, 1)
        result = self.rc.getRoute(Stream('GE', '*', '*', '*'), TW(startD, None))
        self.assertIsInstance(result, RequestMerge,
                              'A RequestMerge object was expected!')
        self.assertEqual(len(result), 1,
                         'Wrong number of data centers for GE.*.*.*!')
        self.assertEqual(result[0]['url'], expURL,
                         'Wrong URL for GE.*.*.*')
        self.assertEqual(result[0]['name'], 'dataselect',
                         'Wrong service name!')

    def testDS_GE_RO(self):
        """Dataselect GE,RO.*.*.*"""

        expURL_GE = 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query'
        expURL_RO = 'http://eida-sc3.infp.ro/fdsnws/dataselect/1/query'

        result = self.rc.getRoute(Stream('GE', '*', '*', '*'), TW(None, None))
        result.extend(self.rc.getRoute(Stream('RO', '*', '*', '*'), TW(None, None)))
        self.assertIsInstance(result, RequestMerge,
                              'A RequestMerge object was expected!')
        self.assertEqual(len(result), 2,
                         'Wrong number of data centers for GE,RO.*.*.*!')
        self.assertEqual(result[0]['url'], expURL_GE,
                         'Wrong URL for GE.*.*.*')
        self.assertEqual(result[0]['name'], 'dataselect',
                         'Wrong service name!')
        self.assertEqual(result[1]['url'], expURL_RO,
                         'Wrong URL for RO.*.*.*')
        self.assertEqual(result[1]['name'], 'dataselect',
                         'Wrong service name!')

    def testDS_GE_APE(self):
        "Dataselect GE.APE.*.*"

        expURL = 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query'
        result = self.rc.getRoute(Stream('GE', 'APE', '*', '*'), TW(None, None))
        self.assertIsInstance(result, RequestMerge,
                              'A RequestMerge object was expected!')
        self.assertEqual(len(result), 1,
                         'Wrong number of data centers for GE.APE.*.*!')
        self.assertEqual(result[0]['url'], expURL,
                         'Wrong URL for GE.APE.*.*!')
        self.assertEqual(result[0]['name'], 'dataselect',
                         'Wrong service name!')

    def testDS_CH_LIENZ_HHZ(self):
        """Dataselect CH.LIENZ.*.HHZ"""

        expURL = 'http://eida.ethz.ch/fdsnws/dataselect/1/query'
        result = self.rc.getRoute(Stream('CH', 'LIENZ', '*', 'HHZ'), TW(None, None))
        self.assertIsInstance(result, RequestMerge,
                              'A RequestMerge object was expected!')
        self.assertEqual(len(result), 1,
                         'Wrong number of data centers for CH.LIENZ.*.HHZ!')
        self.assertEqual(result[0]['url'], expURL,
                         'Wrong URL for CH.LIENZ.*.HHZ!')
        self.assertEqual(result[0]['name'], 'dataselect',
                         'Wrong service name!')

    def testDS_CH_LIENZ_BHZ(self):
        """Dataselect CH.LIENZ.*.BHZ"""

        expURL = 'http://eida.ethz.ch/fdsnws/dataselect/1/query'
        result = self.rc.getRoute(Stream('CH', 'LIENZ', '*', 'BHZ'), TW(None, None))
        self.assertIsInstance(result, RequestMerge,
                              'A RequestMerge object was expected!')
        self.assertEqual(len(result), 1,
                         'Wrong number of data centers for CH.LIENZ.*.BHZ!')
        self.assertEqual(result[0]['url'], expURL,
                         'Wrong URL for CH.LIENZ.*.BHZ!')
        self.assertEqual(result[0]['name'], 'dataselect',
                         'Wrong service name!')

    def testDS_RO_BZS_BHZ(self):
        """Dataselect RO.BZS.*.BHZ"""

        expURL = 'http://eida-sc3.infp.ro/fdsnws/dataselect/1/query'
        result = self.rc.getRoute(Stream('RO', 'BZS', '*', 'BHZ'), TW(None, None))
        self.assertIsInstance(result, RequestMerge,
                              'A RequestMerge object was expected!')
        self.assertEqual(len(result), 1,
                         'Wrong number of data centers for RO.BZS.*.BHZ!')
        self.assertEqual(result[0]['url'], expURL,
                         'Wrong URL for RO.BZS.*.BHZ!')
        self.assertEqual(result[0]['name'], 'dataselect',
                         'Wrong service name!')


# ----------------------------------------------------------------------
def usage():
    print('testRoute [-h] [-p]')


if __name__ == '__main__':

    # 0=Plain mode (good for printing); 1=Colourful mode
    mode = 1

    for ind in range(len(sys.argv)-1, -1, -1):
        if ind == 0:
            break
        if sys.argv[ind] in ('-p', '--plain'):
            sys.argv.pop(ind)
            mode = 0
        elif sys.argv[ind] in ('-h', '--help'):
            usage()
            sys.exit(0)

    unittest.main(testRunner=WITestRunner(mode=mode))
