#!/usr/bin/env python

import sys
import unittest
import urllib2
from unittestTools import WITestRunner
from difflib import Differ


class RouteCacheTests(unittest.TestCase):
    """Test the functionality of routing.py

    """

    @classmethod
    def setUp(cls):
        "Setting up test"
        cls.host = host

    def test_info(self):
        "the 'info' method"

        if self.host.endswith('query'):
            infomethod = '%sinfo' % self.host[:-len('query')]
        else:
            pass

        req = urllib2.Request(infomethod)
        try:
            u = urllib2.urlopen(req)
            buffer = u.read()
        except:
            msg = 'Error calling the "info" method'
            self.assertTrue(False, msg)

        # Check that the length is at least 1
        msg = 'Error "info" method does not return a valid text'
        self.assertGreater(len(buffer), 0, msg)


    def test_version(self):
        "the 'version' method"

        if self.host.endswith('query'):
            vermethod = '%sversion' % self.host[:-len('query')]
        else:
            pass

        req = urllib2.Request(vermethod)
        try:
            u = urllib2.urlopen(req)
            buffer = u.read()
        except:
            raise Exception('Error retrieving version number')

        # Check that it has three components (ints) separated by '.'
        components = buffer.split('.')
        msg = 'Version number does not include the three components'
        self.assertEqual(len(components), 3, msg)

        try:
            components = map(int, components)
        except ValueError:
            msg = 'Components of the version number seem not to be integers.'
            self.assertEqual(1, 0, msg)

    def testDS_GE(self):
        "Dataselect GE.*.*.*"

        req = urllib2.Request(self.host + '?net=GE&format=json')
        try:
            u = urllib2.urlopen(req)
            buffer = u.read()
        except:
            raise Exception('Error retrieving data for GE.*.*.*')

        expected = '[{"url": "http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query", "params": [{"loc": "*", "end": "", "sta": "*", "cha": "*", "priority": 1, "start": "1993-01-01T00:00:00", "net": "GE"}], "name": "dataselect"}]'

        numErrors = 0
        errors = []
        d = Differ()
        for line in d.compare([buffer], [expected]):
            if line[:2] != '  ':
                numErrors += 1
                errors.append(line)

        if numErrors:
            print '\n', '\n'.join(errors)
            self.assertEqual(0, 1, 'Error in %d lines' % len(errors))

    def testDS_GE_RO(self):
        "Dataselect GE,RO.*.*.*"

        req = urllib2.Request(self.host + '?net=GE,RO&format=json')
        try:
            u = urllib2.urlopen(req)
            buffer = u.read()
        except:
            raise Exception('Error retrieving data for GE,RO.*.*.*')

        expected = '[{"url": "http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query", "params": [{"loc": "*", "end": "", "sta": "*", "cha": "*", "priority": 1, "start": "1993-01-01T00:00:00", "net": "GE"}], "name": "dataselect"}, {"url": "http://eida-sc3.infp.ro/fdsnws/dataselect/1/query", "params": [{"loc": "*", "end": "", "sta": "*", "cha": "*", "priority": 1, "start": "1980-01-01T00:00:00", "net": "RO"}], "name": "dataselect"}]'

        numErrors = 0
        errors = []
        d = Differ()
        for line in d.compare([buffer], [expected]):
            if line[:2] != '  ':
                numErrors += 1
                errors.append(line)

        if numErrors:
            print '\n', '\n'.join(errors)
            self.assertEqual(0, 1, 'Error in %d lines' % len(errors))

    def testDS_GE_APE(self):
        "Dataselect GE.APE.*.*"

        req = urllib2.Request(self.host + '?net=GE&sta=APE&format=json')
        try:
            u = urllib2.urlopen(req)
            buffer = u.read()
        except:
            raise Exception('Error retrieving data for GE.APE.*.*')

        expected = '[{"url": "http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query", "params": [{"loc": "*", "end": "", "sta": "APE", "cha": "*", "priority": 1, "start": "1993-01-01T00:00:00", "net": "GE"}], "name": "dataselect"}]'

        numErrors = 0
        errors = []
        d = Differ()
        for line in d.compare([buffer], [expected]):
            if line[:2] != '  ':
                numErrors += 1
                errors.append(line)

        if numErrors:
            print '\n', '\n'.join(errors)
            self.assertEqual(0, 1, 'Error in %d lines' % len(errors))

    def testDS_CH_LIENZ_HHZ(self):
        "Dataselect CH.LIENZ.*.HHZ"

        req = urllib2.Request(self.host + '?net=CH&sta=LIENZ&cha=HHZ&format=json')
        try:
            u = urllib2.urlopen(req)
            buffer = u.read()
        except:
            raise Exception('Error retrieving data for CH.LIENZ.*.HHZ')

        expected = '[{"url": "http://eida.ethz.ch/fdsnws/dataselect/1/query", "params": [{"loc": "*", "end": "", "sta": "LIENZ", "cha": "HHZ", "priority": 1, "start": "1980-01-01T00:00:00", "net": "CH"}], "name": "dataselect"}]'

        numErrors = 0
        errors = []
        d = Differ()
        for line in d.compare([buffer], [expected]):
            if line[:2] != '  ':
                numErrors += 1
                errors.append(line)

        if numErrors:
            print '\n', '\n'.join(errors)
            self.assertEqual(0, 1, 'Error in %d lines' % len(errors))

    def testDS_CH_LIENZ_BHZ(self):
        "Dataselect CH.LIENZ.*.BHZ"

        req = urllib2.Request(self.host + '?net=CH&sta=LIENZ&cha=BHZ&format=json')
        try:
            u = urllib2.urlopen(req)
            buffer = u.read()
        except:
            raise Exception('Error retrieving data for CH.LIENZ.*.BHZ')

        expected = '[{"url": "http://www.orfeus-eu.org/fdsnws/dataselect/1/query", "params": [{"loc": "*", "end": "", "sta": "LIENZ", "cha": "BHZ", "priority": 2, "start": "1980-01-01T00:00:00", "net": "CH"}], "name": "dataselect"}]'

        numErrors = 0
        errors = []
        d = Differ()
        for line in d.compare([buffer], [expected]):
            if line[:2] != '  ':
                numErrors += 1
                errors.append(line)

        if numErrors:
            print '\n', '\n'.join(errors)
            self.assertEqual(0, 1, 'Error in %d lines' % len(errors))

    def testDS_CH_LIENZ_qHZ(self):
        "Dataselect CH.LIENZ.*.?HZ"

        req = urllib2.Request(self.host +
                              '?net=CH&sta=LIENZ&cha=?HZ&format=json')
        try:
            u = urllib2.urlopen(req)
            buffer = u.read()
        except:
            raise Exception('Error retrieving data for CH.LIENZ.*.?HZ')

        expected = '[{"url": "http://www.orfeus-eu.org/fdsnws/dataselect/1/query", "params": [{"loc": "*", "end": "", "sta": "LIENZ", "cha": "BHZ", "priority": 2, "start": "1980-01-01T00:00:00", "net": "CH"}], "name": "dataselect"}, {"url": "http://eida.ethz.ch/fdsnws/dataselect/1/query", "params": [{"loc": "*", "end": "", "sta": "LIENZ", "cha": "LHZ", "priority": 1, "start": "1980-01-01T00:00:00", "net": "CH"}, {"loc": "*", "end": "", "sta": "LIENZ", "cha": "HHZ", "priority": 1, "start": "1980-01-01T00:00:00", "net": "CH"}], "name": "dataselect"}]'

        numErrors = 0
        errors = []
        d = Differ()
        for line in d.compare([buffer], [expected]):
            if line[:2] != '  ':
                numErrors += 1
                errors.append(line)

        if numErrors:
            print '\n', '\n'.join(errors)
            self.assertEqual(0, 1, 'Error in %d lines' % len(errors))

    def testDS_RO_BZS_BHZ(self):
        "Dataselect RO.BZS.*.BHZ"

        req = urllib2.Request(self.host +
                              '?net=RO&sta=BZS&cha=BHZ&format=json')
        try:
            u = urllib2.urlopen(req)
            buffer = u.read()
        except:
            raise Exception('Error retrieving data for RO.BZS.*.BHZ')

        expected = '[{"url": "http://eida-sc3.infp.ro/fdsnws/dataselect/1/query", "params": [{"loc": "*", "end": "", "sta": "BZS", "cha": "BHZ", "priority": 1, "start": "1980-01-01T00:00:00", "net": "RO"}], "name": "dataselect"}]'

        numErrors = 0
        errors = []
        d = Differ()
        for line in d.compare([buffer], [expected]):
            if line[:2] != '  ':
                numErrors += 1
                errors.append(line)

        if numErrors:
            print '\n', '\n'.join(errors)
            self.assertEqual(0, 1, 'Error in %d lines' % len(errors))


# ----------------------------------------------------------------------
def usage():
    print 'testService [-h] [-p]\ntestService [-u http://server/path]'

global host

host = 'http://localhost/eidaws/routing/1/query'

if __name__ == '__main__':

    # 0=Plain mode (good for printing); 1=Colourful mode
    mode = 1

    # The default host is localhost
    for ind, arg in enumerate(sys.argv):
        if arg in ('-p', '--plain'):
            del sys.argv[ind]
            mode = 0
        elif arg == '-u':
            host = sys.argv[ind + 1]
            del sys.argv[ind + 1]
            del sys.argv[ind]
        elif arg in ('-h', '--help'):
            usage()
            sys.exit(0)

    unittest.main(testRunner=WITestRunner(mode=mode))
