#!/usr/bin/env python

import sys
import unittest
from unittestTools import WITestRunner
from routing import RoutingCache


class RouteCacheTests(unittest.TestCase):
    """Test the functionality of routing.py

    """

    @classmethod
    def setUp(cls):
        "Setting up test"
        if hasattr(cls, 'rc'):
            return
        cls.rc = RoutingCache('./routing.xml', './Arclink-inventory.xml',
                              './masterTable.xml')

    def testDS_GE(self):
        "Dataselect GE.*.*.*"

        expectedURL = 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query'
        result = self.rc.getRoute('GE')
        self.assertEqual(len(result), 1,
                         'Wrong number of data centers for GE.*.*.*!')
        self.assertEqual(result[0]['url'], expectedURL,
                         'Wrong URL for GE network!')
        self.assertEqual(result[0]['name'], 'dataselect',
                         'Wrong service name!')

    def testDS_GE_APE(self):
        "Dataselect GE.APE.*.*"

        expectedURL = 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query'
        result = self.rc.getRoute('GE', 'APE')
        self.assertEqual(len(result), 1,
                         'Wrong number of data centers for GE.APE.*.*!')
        self.assertEqual(result[0]['url'], expectedURL,
                         'Wrong URL for GE network!')
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
