#!/usr/bin/env python

"""Tests to check that Routing Service is working

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

   :Copyright:
       2014-2017 Javier Quinteros, GEOFON, GFZ Potsdam <geofon@gfz-potsdam.de>
   :License:
       GPLv3
   :Platform:
       Linux

.. moduleauthor:: Javier Quinteros <javier@gfz-potsdam.de>, GEOFON, GFZ Potsdam
"""

import sys
import os
import datetime
import unittest
import urllib2
from urlparse import urlparse
import json
from difflib import Differ
from xml.dom.minidom import parseString

here = os.path.dirname(__file__)
sys.path.append(os.path.join(here, '..'))
from routeutils.unittestTools import WITestRunner

import ConfigParser


class RouteCacheTests(unittest.TestCase):
    """Test the functionality of routing.py."""

    @classmethod
    def setUp(cls):
        """Setting up test."""
        cls.host = host

    def test_issue_5(self):
        """Filter stations by location."""
        q = '%s?minlat=-31&maxlat=0&minlon=-70&maxlon=0&net=GE&format=post'
        req = urllib2.Request(q % self.host)
        try:
            u = urllib2.urlopen(req)
            buf = u.read()
        except urllib2.URLError:
            msg = 'Error while filtering routes by location.'
            self.assertTrue(False, msg)
            return

        msg = 'The usage of a cache (station names and geographical ' + \
              'locations) to further filter the routes based on a station ' + \
              'was not successful (Old version? See Issue 5: ' + \
              'https://github.com/EIDA/routing/issues/5 ).'

        lines = buf.splitlines()
        dc = lines.pop(0)
        self.assertTrue(urlparse(dc).netloc.endswith('gfz-potsdam.de'), msg)

        msg = 'Error: GE must be the network of the station!'

        for line in lines:
            if not len(line):
                continue
            self.assertEqual(line.split()[0], 'GE', msg)
            self.assertTrue(line.split()[1] in ('LVC', 'RIOB'),
                            'Wrong station name! LVC or RIOB expected.')

    def test_issue_19(self):
        """Caching of station names."""
        req = urllib2.Request('%s?sta=BNDI&format=post' % self.host)
        try:
            u = urllib2.urlopen(req)
            buf = u.read()
        except urllib2.URLError:
            msg = 'Error while requesting routes based on a station name.'
            self.assertTrue(False, msg)
            return

        msg = 'The usage of a cache (station names and geographical ' + \
              'locations) to further filter the routes based on a station ' + \
              'was not successful (Old version? See Issue 19: ' + \
              'https://github.com/EIDA/routing/issues/19 ).'

        lines = buf.splitlines()
        dc = lines.pop(0)
        self.assertTrue(urlparse(dc).netloc.endswith('gfz-potsdam.de'), msg)

        msg = 'Error: GE must be the network of the station!'

        for line in lines:
            if not len(line):
                continue
            self.assertEqual(line.split()[0], 'GE', msg)
            self.assertEqual(line.split()[1], 'BNDI', 'Wrong station name!')

    def test_issue_11(self):
        """Dynamic creation of application.wadl."""
        req = urllib2.Request('%sapplication.wadl' % self.host[:-len('query')])
        try:
            u = urllib2.urlopen(req)
            buf = u.read()
        except urllib2.URLError:
            msg = 'The file application.wadl cannot be built (missing ' + \
                '"baseUrl" in config file?)'
            self.assertTrue(False, msg)
            return

        msg = 'The baseURL in the application.wadl is not the same as ' + \
            'the one used to do the query. (Old version? See Issue 11: ' + \
            'https://github.com/EIDA/routing/issues/11 ).'

        dom = parseString(buf)
        for res in dom.getElementsByTagName('resources'):
            self.assertTrue(self.host.startswith(res.getAttribute('base')),
                            msg)

    def test_long_URI(self):
        """Very large URI."""
        msg = 'A URI of more than 2000 characters is not allowed and ' + \
            'should return a 414 error code'
        req = urllib2.Request('%s?net=GE%s' % (self.host, '&net=GE' * 500))
        try:
            u = urllib2.urlopen(req)
            u.read()
        except urllib2.URLError as e:
            self.assertEqual(e.code, 414, msg)
            return

        self.assertTrue(False, msg)
        return

    def test_issue_2(self):
        """Proper POST format when enddate is missing."""
        msg = 'Found a bug which has already been fixed (see Issue 2: '
        msg = msg + 'https://github.com/EIDA/routing/issues/2 ).'
        req = urllib2.Request('%s?start=2015-01-01&format=post' % self.host)
        try:
            u = urllib2.urlopen(req)
            u.read()
        except urllib2.URLError:
            self.assertTrue(False, msg)

        return

    def test_issue_8(self):
        """Proper parsing of start and end dates."""
        msg = 'Found a bug which has already been fixed (see Issue 8: '
        msg = msg + 'https://github.com/EIDA/routing/issues/8 ).'
        req = urllib2.Request('%s?start=2013-01-01&end=2016-12-31' % self.host)
        try:
            u = urllib2.urlopen(req)
            u.read()
        except urllib2.URLError:
            self.assertTrue(False, msg)

        return

    def test_issue_16(self):
        """Wrong data type (datetime) when format=post."""
        msg = 'Found a bug which has already been fixed (see Issue 16: '
        msg = msg + 'https://github.com/EIDA/routing/issues/16 ).'
        q = '%s?format=post&start=2013-01-01T00:00:00&end=2016-12-31T00:00:00'
        req = urllib2.Request(q % self.host)
        try:
            u = urllib2.urlopen(req)
            u.read()
        except urllib2.URLError:
            self.assertTrue(False, msg)

        return

    def test_wrong_parameter(self):
        """Unknown parameter."""
        msg = 'An error code 400 Bad Request is expected for an unknown ' + \
            'parameter'
        req = urllib2.Request('%s?net=GE&wrongparam=1' % self.host)
        try:
            u = urllib2.urlopen(req)
            u.read()
        except urllib2.URLError as e:
            self.assertEqual(e.code, 400, msg)
            return

        self.assertTrue(False, msg)
        return

    def testDS_XXX(self):
        """Non-existing network XXX."""
        req = urllib2.Request('%s?net=XXX' % self.host)
        msg = 'An error code 204 No Content is expected for an unknown network'
        try:
            u = urllib2.urlopen(req)
            u.read()
            self.assertEqual(u.getcode(), 204, '%s (%s)' % (msg, u.getcode()))
            return
        except urllib2.URLError as e:
            if hasattr(e, 'code'):
                self.assertEqual(e.code, 204, '%s (%s)' % (msg, e.code))
                return
            else:
                self.assertTrue(False, '%s (%s)' % (msg, e))
                return

        except Exception as e:
            self.assertTrue(False, '%s (%s)' % (msg, e))
            return

    def test_wrong_alternative(self):
        """Wrong values in alternative parameter."""
        # Test with an integer > 1
        value = 2
        msg = 'A %s in the alternative parameter is expected' % type(value) + \
            ' to raise an error code 400'
        req = urllib2.Request('%s?net=GE&alternative=%s' % (self.host, value))
        try:
            u = urllib2.urlopen(req)
            u.read()
            self.assertTrue(False, msg)
        except urllib2.URLError as e:
            self.assertEqual(e.code, 400, msg)

        # Test with 1
        value = 1
        msg = 'A %s in the alternative parameter is expected' % type(value) + \
            ' to raise an error code 400'
        req = urllib2.Request('%s?net=GE&alternative=%s' % (self.host, value))
        try:
            u = urllib2.urlopen(req)
            u.read()
            self.assertTrue(False, msg)
        except urllib2.URLError as e:
            self.assertEqual(e.code, 400, msg)

        # Test with 0
        value = 0
        msg = 'A %s in the alternative parameter is expected' % type(value) + \
            ' to raise an error code 400'
        req = urllib2.Request('%s?net=GE&alternative=%s' % (self.host, value))
        try:
            u = urllib2.urlopen(req)
            u.read()
            self.assertTrue(False, msg)
        except urllib2.URLError as e:
            self.assertEqual(e.code, 400, msg)

        # Test with a float
        value = 8.5
        msg = 'A %s in the alternative parameter is expected' % type(value) + \
            ' to raise an error code 400'
        req = urllib2.Request('%s?net=GE&alternative=%s' % (self.host, value))
        try:
            u = urllib2.urlopen(req)
            u.read()
            self.assertTrue(False, msg)
        except urllib2.URLError as e:
            self.assertEqual(e.code, 400, msg)

        # Test with a random string
        value = 'skjndfvkjsn'
        msg = 'A %s in the alternative parameter is expected' % type(value) + \
            ' to raise an error code 400'
        req = urllib2.Request('%s?net=GE&alternative=%s' % (self.host, value))
        try:
            u = urllib2.urlopen(req)
            u.read()
            self.assertTrue(False, msg)
        except urllib2.URLError as e:
            self.assertEqual(e.code, 400, msg)

        return

    def test_alternative_format_get(self):
        """Incompatibility between alternative=true and format=get."""
        req = urllib2.Request('%s?net=GE&format=get&alternative=true' %
                              self.host)
        msg = 'When a wrong format is specified an error code 400 is expected!'
        try:
            u = urllib2.urlopen(req)
            u.read()
        except urllib2.URLError as e:
            self.assertEqual(e.code, 400, msg)
            return

        self.assertTrue(False, msg)
        return

    def test_wrong_format(self):
        """Wrong format option."""
        req = urllib2.Request('%s?net=GE&format=WRONGFORMAT' %
                              self.host)
        msg = 'When a wrong format is specified an error code 400 is expected!'
        try:
            u = urllib2.urlopen(req)
            u.read()
        except urllib2.URLError as e:
            if hasattr(e, 'code'):
                self.assertEqual(e.code, 400, '%s (%s)' % (msg, e.code))
                return

            self.assertTrue(False, '%s (%s)' % (msg, e))
            return

        self.assertTrue(False, msg)
        return

    def test_wrong_datetime(self):
        """Swap start and end time."""
        d1 = datetime.datetime(2004, 1, 1)
        d2 = d1 - datetime.timedelta(days=1)
        req = urllib2.Request('%s?net=GE&start=%s&end=%s' % (self.host,
                                                             d1.isoformat(),
                                                             d2.isoformat()))
        msg = 'When starttime > endtime an error code 400 is expected!'
        try:
            u = urllib2.urlopen(req)
            u.read()
        except urllib2.URLError as e:
            self.assertEqual(e.code, 400, msg)
            return

        self.assertTrue(False, msg)
        return

    def test_application_wadl(self):
        """'application.wadl' method."""
        if self.host.endswith('query'):
            appmethod = '%sapplication.wadl' % self.host[:-len('query')]
        else:
            pass

        req = urllib2.Request(appmethod)
        try:
            u = urllib2.urlopen(req)
            buffer = u.read()
        except:
            msg = 'Error calling the "application.wadl" method'
            self.assertTrue(False, msg)

        msg = 'The "application.wadl" method returned an empty string'
        self.assertGreater(len(buffer), 0, msg)
        msg = 'The file returned by "application.wadl" does not contain a "<"'
        self.assertIn('<', buffer, msg)

        # Check that the returned value is a valid xml file
        msg = 'Error! application.wadl method does not return a valid xml file'
        try:
            parseString(buffer)
        except:
            self.assertTrue(False, msg)

    def test_info(self):
        """'info' method."""
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
        """'version' method."""
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
        # Check for exact version
        self.assertEqual(components, [1, 1, 0], 'Version is not 1.1.0 !')

    def testDS_VirtualNetwork(self):
        """Dataselect _GEALL.*.*.* ."""
        expec = {
                 'GE': 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query'
                }
        req = urllib2.Request(self.host + '?net=_GEALL&format=json')
        try:
            u = urllib2.urlopen(req)
            buffer = u.read()
        except:
            raise Exception('Error retrieving data for _GEALL.*.*.*')

        result = json.loads(buffer)

        for node in result:
            self.assertEqual(node['name'], 'dataselect',
                             'Service of node is not dataselect!')

            self.assertTrue(node['params'][0]['net'] == 'GE',
                            '%s is not the expected network' %
                            node['params'][0]['net'])

            self.assertEqual(expec[node['params'][0]['net']],
                             node['url'],
                             'URL for network %s is not from %s!' %
                             (node['params'][0]['net'],
                              expec[node['params'][0]['net']]))

    def testDS_VirtualNetwork2(self):
        """Dataselect _GEALL.AP*.*.* ."""
        expec = {
                 'GE': 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query'
                }
        req = urllib2.Request(self.host + '?net=_GEALL&sta=AP*&format=json')
        try:
            u = urllib2.urlopen(req)
            buffer = u.read()
        except:
            raise Exception('Error retrieving data for _GEALL.*.*.*')

        result = json.loads(buffer)

        for node in result:
            self.assertEqual(node['name'], 'dataselect',
                             'Service of node is not dataselect!')

            for params in node['params']:
                self.assertEqual(params['net'], 'GE',
                                 '%s is not the expected network' %
                                 params['net'])

                self.assertEqual(params['sta'], 'APE',
                                 '%s is not the expected station' %
                                 params['sta'])

                self.assertEqual(expec[params['net']], node['url'],
                                 'URL for network %s is not from %s!' %
                                 (params['net'], expec[params['net']]))

    def testDS_ZE(self):
        """Dataselect ZE.*.*.* ."""
        req = urllib2.Request(self.host + '?net=ZE&format=json')
        try:
            u = urllib2.urlopen(req)
            buffer = u.read()
        except:
            raise Exception('Error retrieving data for ZE.*.*.*')

        result = json.loads(buffer)

        for node in result:
            self.assertEqual(node['name'], 'dataselect',
                             'Service of node is not dataselect!')

            self.assertEqual(len(node['params']), 4,
                            '4 epochs are expected from the ZE network')

    def testDS_GE(self):
        """Dataselect GE.*.*.* ."""
        req = urllib2.Request(self.host + '?net=GE&format=json')
        try:
            u = urllib2.urlopen(req)
            buffer = u.read()
        except:
            raise Exception('Error retrieving data for GE.*.*.*')

        expected = '[{"url": ' + \
            '"http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query", ' + \
            '"params": [{"loc": "*", "end": "", "sta": "*", "cha": "*", ' + \
            '"priority": 1, "start": "1993-01-01T00:00:00", "net": "GE"}], ' +\
            '"name": "dataselect"}]'

        numErrors = 0
        errors = []
        d = Differ()
        for line in d.compare([buffer], [expected]):
            if line[:2] != '  ':
                numErrors += 1
                errors.append(line)

        if numErrors:
            print('\n' + '\n'.join(errors))
            self.assertEqual(0, 1, 'Error in %d lines' % len(errors))

    def testDS_GE_RO(self):
        """Dataselect GE,RO.*.*.* ."""
        expec = {
                 'RO': 'http://eida-sc3.infp.ro/fdsnws/dataselect/1/query',
                 'GE': 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query'
                }

        req = urllib2.Request(self.host + '?net=GE,RO&format=json')
        try:
            u = urllib2.urlopen(req)
            buffer = u.read()
        except:
            raise Exception('Error retrieving data for GE,RO.*.*.*')

        result = json.loads(buffer)

        for node in result:
            self.assertEqual(node['name'], 'dataselect',
                             'Service of node is not dataselect!')

            self.assertTrue(node['params'][0]['net'] in expec.keys(),
                            '%s is not a requested network' %
                            node['params'][0]['net'])

            self.assertEqual(expec[node['params'][0]['net']],
                             node['url'],
                             'URL for network %s is not from %s!' %
                             (node['params'][0]['net'],
                              expec[node['params'][0]['net']]))

    def testDS_GE_APE(self):
        """Dataselect GE.APE.*.* ."""
        req = urllib2.Request(self.host + '?net=GE&sta=APE&format=json')
        try:
            u = urllib2.urlopen(req)
            buffer = u.read()
        except:
            raise Exception('Error retrieving data for GE.APE.*.*')

        expected = '[{"url": ' + \
            '"http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query", ' + \
            '"params": [{"loc": "*", "end": "", "sta": "APE", "cha": "*", ' + \
            '"priority": 1, "start": "1993-01-01T00:00:00", "net": "GE"}], ' +\
            '"name": "dataselect"}]'

        numErrors = 0
        errors = []
        d = Differ()
        for line in d.compare([buffer], [expected]):
            if line[:2] != '  ':
                numErrors += 1
                errors.append(line)

        if numErrors:
            print('\n' + '\n'.join(errors))
            self.assertEqual(0, 1, 'Error in %d lines' % len(errors))

    def testDS_CH_LIENZ_HHZ(self):
        """Dataselect CH.LIENZ.*.HHZ ."""
        req = urllib2.Request('%s?net=CH&sta=LIENZ&cha=HHZ&format=json' %
                              self.host)
        try:
            u = urllib2.urlopen(req)
            buffer = u.read()
        except:
            raise Exception('Error retrieving data for CH.LIENZ.*.HHZ')

        expected = '[{"url": ' + \
            '"http://eida.ethz.ch/fdsnws/dataselect/1/query", "params": ' + \
            '[{"loc": "*", "end": "", "sta": "LIENZ", "cha": "HHZ", ' + \
            '"priority": 1, "start": "1980-01-01T00:00:00", "net": "CH"}], ' +\
            '"name": "dataselect"}]'

        numErrors = 0
        errors = []
        d = Differ()
        for line in d.compare([buffer], [expected]):
            if line[:2] != '  ':
                numErrors += 1
                errors.append(line)

        if numErrors:
            print('\n' + '\n'.join(errors))
            self.assertEqual(0, 1, 'Error in %d lines' % len(errors))

    def testDS_CH_LIENZ_BHZ(self):
        """Dataselect CH.LIENZ.*.BHZ ."""
        req = urllib2.Request('%s?net=CH&sta=LIENZ&cha=BHZ&format=json' %
                              self.host)
        try:
            u = urllib2.urlopen(req)
            buffer = u.read()
        except:
            raise Exception('Error retrieving data for CH.LIENZ.*.BHZ')

        expected = '[{"url": ' + \
            '"http://eida.ethz.ch/fdsnws/dataselect/1/query", "params": ' + \
            '[{"loc": "*", "end": "", "sta": "LIENZ", "cha": "BHZ", ' + \
            '"priority": 1, "start": "1980-01-01T00:00:00", "net": "CH"}], ' +\
            '"name": "dataselect"}]'
        # expected = '[{"url": ' + \
        #     '"http://www.orfeus-eu.org/fdsnws/dataselect/1/query", ' + \
        #     '"params": [{"loc": "*", "end": "", "sta": "LIENZ", "cha": ' + \
        #     '"BHZ", "priority": 2, "start": "1980-01-01T00:00:00", "net": ' +
        #     '"CH"}], "name": "dataselect"}]'

        numErrors = 0
        errors = []
        d = Differ()
        for line in d.compare([buffer], [expected]):
            if line[:2] != '  ':
                numErrors += 1
                errors.append(line)

        if numErrors:
            print('\n' + '\n'.join(errors))
            self.assertEqual(0, 1, 'Error in %d lines' % len(errors))

    # def testDS_CH_LIENZ_qHZ(self):
    #     "Dataselect CH.LIENZ.*.?HZ"

    #     req = urllib2.Request('%s?net=CH&sta=LIENZ&cha=?HZ&format=json' %
    #                           self.host)
    #     try:
    #         u = urllib2.urlopen(req)
    #         buffer = u.read()
    #     except:
    #         raise Exception('Error retrieving data for CH.LIENZ.*.?HZ')

    #     expected = '[{"url": ' + \
    #         '"http://www.orfeus-eu.org/fdsnws/dataselect/1/query", ' + \
    #         '"params": [{"loc": "*", "end": "", "sta": "LIENZ", "cha": ' + \
    #         '"BHZ", "priority": 2, "start": "1980-01-01T00:00:00", ' + \
    #         '"net": "CH"}], "name": "dataselect"}, {"url": ' + \
    #         '"http://eida.ethz.ch/fdsnws/dataselect/1/query", "params": ' + \
    #         '[{"loc": "*", "end": "", "sta": "LIENZ", "cha": "LHZ", ' + \
    #         '"priority": 1, "start": "1980-01-01T00:00:00", "net": "CH"}, ' +
    #         '{"loc": "*", "end": "", "sta": "LIENZ", "cha": "HHZ", ' + \
    #         '"priority": 1, "start": "1980-01-01T00:00:00", "net": "CH"}], '+
    #         '"name": "dataselect"}]'

    #     numErrors = 0
    #     errors = []
    #     d = Differ()
    #     for line in d.compare([buffer], [expected]):
    #         if line[:2] != '  ':
    #             numErrors += 1
    #             errors.append(line)

    #     if numErrors:
    #         print '\n', '\n'.join(errors)
    #         self.assertEqual(0, 1, 'Error in %d lines' % len(errors))

    def testDS_RO_BZS_BHZ(self):
        """Dataselect RO.BZS.*.BHZ ."""
        req = urllib2.Request('%s?net=RO&sta=BZS&cha=BHZ&format=json' %
                              self.host)
        try:
            u = urllib2.urlopen(req)
            buffer = u.read()
        except:
            raise Exception('Error retrieving data for RO.BZS.*.BHZ')

        expected = '[{"url": ' + \
            '"http://eida-sc3.infp.ro/fdsnws/dataselect/1/query", ' + \
            '"params": [{"loc": "*", "end": "", "sta": "BZS", "cha": ' + \
            '"BHZ", "priority": 1, "start": "1980-01-01T00:00:00", "net": ' + \
            '"RO"}], "name": "dataselect"}]'

        numErrors = 0
        errors = []
        d = Differ()
        for line in d.compare([buffer], [expected]):
            if line[:2] != '  ':
                numErrors += 1
                errors.append(line)

        if numErrors:
            print('\n' + '\n'.join(errors))
            self.assertEqual(0, 1, 'Error in %d lines' % len(errors))


# ----------------------------------------------------------------------
def usage():
    """Print how to use the service test."""
    print('testService [-h|--help] [-p|--plain] http://server/path')


global host

if __name__ == '__main__':

    # 0=Plain mode (good for printing); 1=Colourful mode
    mode = 1

    # The default host is the one in the cfg file
    try:
        directory = os.path.dirname(__file__)
        configP = configparser.RawConfigParser()
        configP.read(os.path.join(directory, '..', 'routing.cfg'))
        host = configP.get('Service', 'baseURL')
    except:
        pass

    for ind in range(len(sys.argv)-1, -1, -1):
        if ind == 0:
            break
        if sys.argv[ind] in ('-p', '--plain'):
            sys.argv.pop(ind)
            mode = 0
        elif sys.argv[ind] in ('-h', '--help'):
            usage()
            sys.exit(0)
        else:
            host = sys.argv[ind]
            sys.argv.pop(ind)

    unittest.main(testRunner=WITestRunner(mode=mode))
