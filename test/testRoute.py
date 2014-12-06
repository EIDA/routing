#!/usr/bin/env python

import sys
import os

here = os.path.dirname(__file__)
sys.path.append(os.path.join(here, '..'))

import unittest
from unittestTools import WITestRunner
from routing import RoutingCache
from routing import RequestMerge
from wsgicomm import Logs


class RouteCacheTests(unittest.TestCase):
    """Test the functionality of routing.py

    """

    @classmethod
    def setUp(cls):
        "Setting up test"
        if hasattr(cls, 'rc'):
            return
        cls.rc = RoutingCache('../data/routing.xml',
                              '../data/Arclink-inventory.xml',
                              '../data/masterTable.xml', Logs(1))

    def testDS_GE(self):
        "Dataselect GE.*.*.*"

        expURL = 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query'
        result = self.rc.getRoute('GE')
        self.assertIsInstance(result, RequestMerge,
                              'A RequestMerge object was expected!')
        self.assertEqual(len(result), 1,
                         'Wrong number of data centers for GE.*.*.*!')
        self.assertEqual(result[0]['url'], expURL,
                         'Wrong URL for GE.*.*.*')
        self.assertEqual(result[0]['name'], 'dataselect',
                         'Wrong service name!')

    def testDS_GE_APE(self):
        "Dataselect GE.APE.*.*"

        expURL = 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query'
        result = self.rc.getRoute('GE', 'APE')
        self.assertIsInstance(result, RequestMerge,
                              'A RequestMerge object was expected!')
        self.assertEqual(len(result), 1,
                         'Wrong number of data centers for GE.APE.*.*!')
        self.assertEqual(result[0]['url'], expURL,
                         'Wrong URL for GE.APE.*.*!')
        self.assertEqual(result[0]['name'], 'dataselect',
                         'Wrong service name!')

    def testDS_CH_LIENZ_HHZ(self):
        "Dataselect CH.LIENZ.*.HHZ"

        expURL = 'http://eida.ethz.ch/fdsnws/dataselect/1/query'
        result = self.rc.getRoute('CH', 'LIENZ', '*', 'HHZ')
        self.assertIsInstance(result, RequestMerge,
                              'A RequestMerge object was expected!')
        self.assertEqual(len(result), 1,
                         'Wrong number of data centers for CH.LIENZ.*.HHZ!')
        self.assertEqual(result[0]['url'], expURL,
                         'Wrong URL for CH.LIENZ.*.HHZ!')
        self.assertEqual(result[0]['name'], 'dataselect',
                         'Wrong service name!')

    def testDS_CH_LIENZ_BHZ(self):
        "Dataselect CH.LIENZ.*.BHZ"

        expURL = 'http://www.orfeus-eu.org/fdsnws/dataselect/1/query'
        result = self.rc.getRoute('CH', 'LIENZ', '*', 'BHZ')
        self.assertIsInstance(result, RequestMerge,
                              'A RequestMerge object was expected!')
        self.assertEqual(len(result), 1,
                         'Wrong number of data centers for CH.LIENZ.*.BHZ!')
        self.assertEqual(result[0]['url'], expURL,
                         'Wrong URL for CH.LIENZ.*.BHZ!')
        self.assertEqual(result[0]['name'], 'dataselect',
                         'Wrong service name!')

    def testDS_CH_LIENZ_qHZ(self):
        "Dataselect CH.LIENZ.*.?HZ"

        odcURL = 'http://www.orfeus-eu.org/fdsnws/dataselect/1/query'
        ethURL = 'http://eida.ethz.ch/fdsnws/dataselect/1/query'
        result = self.rc.getRoute('CH', 'LIENZ', '*', '?HZ')
        self.assertIsInstance(result, RequestMerge,
                              'A RequestMerge object was expected!')
        self.assertEqual(len(result), 2,
                         'Wrong number of data centers for CH.LIENZ.*.?HZ!')

        for res in result:
            if 'eth' in res['url']:
                self.assertEqual(res['url'], ethURL,
                                 'Wrong URL for CH.LIENZ.*.?HZ!')
                self.assertEqual(res['name'], 'dataselect',
                                 'Wrong service name!')

                myStreams = ['LHZ', 'HHZ']
                self.assertEqual(len(res['params']), len(myStreams),
                                 'Wrong number of streams for ETH!')

                for i in res['params']:
                    self.assertIn(i['cha'], myStreams,
                                  '%s is not an expected channel for ETH!'
                                  % i['cha'])
            elif 'orfeus' in res['url']:
                self.assertEqual(res['url'], odcURL,
                                 'Wrong URL for CH.LIENZ.*.?HZ!')
                self.assertEqual(res['name'], 'dataselect',
                                 'Wrong service name!')

                self.assertEqual(len(res['params']), 1,
                                 'Wrong number of streams for ODC!')
                self.assertIn(res['params'][0]['cha'], 'BHZ',
                              '%s is not an expected channel for ETH!' %
                              res['params'][0]['cha'])
            else:
                self.assertEqual(1, 0,
                                 'None of the URLs belong to Orfeus or ETH!')

    def testDS_RO_BZS_BHZ(self):
        "Dataselect RO.BZS.*.BHZ"

        expURL = 'http://eida-sc3.infp.ro/fdsnws/dataselect/1/query'
        result = self.rc.getRoute('RO', 'BZS', '*', 'BHZ')
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
    print 'testRoute [-h] [-p]'


if __name__ == '__main__':

    # 0=Plain mode (good for printing); 1=Colourful mode
    mode = 1

    for ind, arg in enumerate(sys.argv):
        if arg in ('-p', '--plain'):
            del sys.argv[ind]
            mode = 0
        elif arg in ('-h', '--help'):
            usage()
            sys.exit(0)

    unittest.main(testRunner=WITestRunner(mode=mode))
