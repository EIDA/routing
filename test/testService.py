#!/usr/bin/env python3

"""Tests to check that Routing Service is working

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
import unittest

import json
from difflib import Differ
from xml.dom.minidom import parseString

# More Python 3 compatibility
try:
    import urllib.request as ul
except ImportError:
    import urllib2 as ul

here = os.path.dirname(__file__)
sys.path.append(os.path.join(here, '..'))
from routeutils.unittestTools import WITestRunner

# More Python 3 compatibility
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

# More Python 3 compatibility
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


class RouteCacheTests(unittest.TestCase):
    """Test the functionality of routing.py."""

    @classmethod
    def setUp(cls):
        """Setting up test."""
        cls.host = host

    def test_issue_5(self):
        """Filter stations by location."""
        q = '%s?minlat=-31&maxlat=0&minlon=-70&maxlon=-67&net=GE&format=post'
        req = ul.Request(q % self.host)
        try:
            u = ul.urlopen(req)
            buf = u.read().decode('utf-8')
        except ul.URLError:
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
                            'Wrong station name! LVC or RIOB expected. %s found' % line.split()[1])

    def test_issue_19(self):
        """Caching of station names."""
        req = ul.Request('%s?sta=BNDI&format=post' % self.host)
        try:
            u = ul.urlopen(req)
            buf = u.read().decode('utf-8')
        except ul.URLError:
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
        req = ul.Request('%sapplication.wadl' % self.host[:-len('query')])
        try:
            u = ul.urlopen(req)
            buf = u.read().decode('utf-8')
        except ul.URLError:
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
        req = ul.Request('%s?net=GE%s' % (self.host, '&net=GE' * 500))
        try:
            u = ul.urlopen(req)
            u.read().decode('utf-8')
        except ul.URLError as e:
            self.assertEqual(e.code, 414, msg)
            return

        self.assertTrue(False, msg)
        return

    def test_issue_2(self):
        """Proper POST format when enddate is missing."""
        msg = 'Found a bug which has already been fixed (see Issue 2: '
        msg = msg + 'https://github.com/EIDA/routing/issues/2 ).'
        req = ul.Request('%s?start=2015-01-01&format=post' % self.host)
        try:
            u = ul.urlopen(req)
            u.read().decode('utf-8')
        except ul.URLError:
            self.assertTrue(False, msg)

        return

    def test_issue_8(self):
        """Proper parsing of start and end dates."""
        msg = 'Found a bug which has already been fixed (see Issue 8: '
        msg = msg + 'https://github.com/EIDA/routing/issues/8 ).'
        req = ul.Request('%s?start=2013-01-01&end=2016-12-31' % self.host)
        try:
            u = ul.urlopen(req)
            u.read().decode('utf-8')
        except ul.URLError:
            self.assertTrue(False, msg)

        return

    def test_issue_16(self):
        """Wrong data type (datetime) when format=post."""
        msg = 'Found a bug which has already been fixed (see Issue 16: '
        msg = msg + 'https://github.com/EIDA/routing/issues/16 ).'
        q = '%s?format=post&start=2013-01-01T00:00:00&end=2016-12-31T00:00:00'
        req = ul.Request(q % self.host)
        try:
            u = ul.urlopen(req)
            u.read().decode('utf-8')
        except ul.URLError:
            self.assertTrue(False, msg)

        return

    def test_wrong_parameter(self):
        """Unknown parameter."""
        msg = 'An error code 400 Bad Request is expected for an unknown ' + \
            'parameter'
        req = ul.Request('%s?net=GE&wrongparam=1' % self.host)
        try:
            u = ul.urlopen(req)
            u.read().decode('utf-8')
        except ul.URLError as e:
            self.assertEqual(e.code, 400, msg)
            return

        self.assertTrue(False, msg)
        return

    def testDS_XXX(self):
        """Non-existing network XXX."""
        req = ul.Request('%s?net=XXX' % self.host)
        msg = 'An error code 204 No Content is expected for an unknown network'
        try:
            u = ul.urlopen(req)
            u.read().decode('utf-8')
            self.assertEqual(u.getcode(), 204, '%s (%s)' % (msg, u.getcode()))
            return
        except ul.URLError as e:
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
        req = ul.Request('%s?net=GE&alternative=%s' % (self.host, value))
        try:
            u = ul.urlopen(req)
            u.read().decode('utf-8')
            self.assertTrue(False, msg)
        except ul.URLError as e:
            self.assertEqual(e.code, 400, msg)

        # Test with 1
        value = 1
        msg = 'A %s in the alternative parameter is expected' % type(value) + \
            ' to raise an error code 400'
        req = ul.Request('%s?net=GE&alternative=%s' % (self.host, value))
        try:
            u = ul.urlopen(req)
            u.read().decode('utf-8')
            self.assertTrue(False, msg)
        except ul.URLError as e:
            self.assertEqual(e.code, 400, msg)

        # Test with 0
        value = 0
        msg = 'A %s in the alternative parameter is expected' % type(value) + \
            ' to raise an error code 400'
        req = ul.Request('%s?net=GE&alternative=%s' % (self.host, value))
        try:
            u = ul.urlopen(req)
            u.read().decode('utf-8')
            self.assertTrue(False, msg)
        except ul.URLError as e:
            self.assertEqual(e.code, 400, msg)

        # Test with a float
        value = 8.5
        msg = 'A %s in the alternative parameter is expected' % type(value) + \
            ' to raise an error code 400'
        req = ul.Request('%s?net=GE&alternative=%s' % (self.host, value))
        try:
            u = ul.urlopen(req)
            u.read().decode('utf-8')
            self.assertTrue(False, msg)
        except ul.URLError as e:
            self.assertEqual(e.code, 400, msg)

        # Test with a random string
        value = 'skjndfvkjsn'
        msg = 'A %s in the alternative parameter is expected' % type(value) + \
            ' to raise an error code 400'
        req = ul.Request('%s?net=GE&alternative=%s' % (self.host, value))
        try:
            u = ul.urlopen(req)
            u.read().decode('utf-8')
            self.assertTrue(False, msg)
        except ul.URLError as e:
            self.assertEqual(e.code, 400, msg)

        return

    def test_alternative_format_get(self):
        """Incompatibility between alternative=true and format=get."""
        req = ul.Request('%s?net=GE&format=get&alternative=true' %
                              self.host)
        msg = 'When a wrong format is specified an error code 400 is expected!'
        try:
            u = ul.urlopen(req)
            u.read().decode('utf-8')
        except ul.URLError as e:
            self.assertEqual(e.code, 400, msg)
            return

        self.assertTrue(False, msg)
        return

    def test_wrong_format(self):
        """Wrong format option."""
        req = ul.Request('%s?net=GE&format=WRONGFORMAT' %
                              self.host)
        msg = 'When a wrong format is specified an error code 400 is expected!'
        try:
            u = ul.urlopen(req)
            u.read().decode('utf-8')
        except ul.URLError as e:
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
        req = ul.Request('%s?net=GE&start=%s&end=%s' % (self.host,
                                                             d1.isoformat(),
                                                             d2.isoformat()))
        msg = 'When starttime > endtime an error code 400 is expected!'
        try:
            u = ul.urlopen(req)
            u.read().decode('utf-8')
        except ul.URLError as e:
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

        req = ul.Request(appmethod)
        try:
            u = ul.urlopen(req)
            buffer = u.read().decode('utf-8')
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

        req = ul.Request(infomethod)
        try:
            u = ul.urlopen(req)
            buffer = u.read().decode('utf-8')
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

        req = ul.Request(vermethod)
        try:
            u = ul.urlopen(req)
            buffer = u.read().decode('utf-8')
        except:
            raise Exception('Error retrieving version number')

        # Remove information about release (after a minus '-')
        auxversion = buffer.split('-')[0]
        # Check that it has three components (ints) separated by '.'
        components = auxversion.split('.')
        msg = 'Version number does not include the three components'
        self.assertEqual(len(components), 3, msg)

        try:
            components = [x for x in map(int, components)]
        except ValueError:
            msg = 'Components of the version number seem not to be integers.'
            self.assertEqual(1, 0, msg)
        # Check for exact version
        self.assertEqual(components, [1, 2, 1], 'Version is not 1.2.1 !')

    def testDS_VirtualNetwork(self):
        """Dataselect _GEALL.*.*.* ."""
        expec = {
                 'GE': 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query',
                 'DK': 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query',
                 'WM': 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query'
                }
        req = ul.Request(self.host + '?net=_GEALL&format=json')
        try:
            u = ul.urlopen(req)
            buffer = u.read().decode('utf-8')
        except:
            raise Exception('Error retrieving data for _GEALL.*.*.*')

        result = json.loads(buffer)

        for node in result:
            self.assertEqual(node['name'], 'dataselect',
                             'Service of node is not dataselect!')

            self.assertTrue(node['params'][0]['net'] in ('GE', 'DK', 'WM'),
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
        req = ul.Request(self.host + '?net=_GEALL&sta=AP*&format=json')
        try:
            u = ul.urlopen(req)
            buffer = u.read().decode('utf-8')
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

                self.assertIn(params['sta'], ['APE', 'APEZ'],
                                 '%s is not the expected station' %
                                 params['sta'])

                self.assertEqual(expec[params['net']], node['url'],
                                 'URL for network %s is not from %s!' %
                                 (params['net'], expec[params['net']]))

    def testDS_ZE(self):
        """Dataselect ZE.*.*.* ."""
        req = ul.Request(self.host + '?net=ZE&format=json')
        try:
            u = ul.urlopen(req)
            buffer = u.read().decode('utf-8')
        except:
            raise Exception('Error retrieving data for ZE.*.*.*')

        result = json.loads(buffer)

        for node in result:
            self.assertEqual(node['name'], 'dataselect',
                             'Service of node is not dataselect!')

            if 'geofon' in node['url']:
                self.assertEqual(len(node['params']), 4,
                                '4 epochs are expected from the ZE network')

    def testDS_GE(self):
        """Dataselect GE.*.*.* ."""
        req = ul.Request(self.host + '?net=GE&format=json')
        try:
            u = ul.urlopen(req)
            buffer = u.read().decode('utf-8')
        except:
            raise Exception('Error retrieving data for GE.*.*.*')

        jsonBuf = json.loads(buffer)

        self.assertEqual(jsonBuf[0]['name'], 'dataselect',
                         'Service of node is not dataselect!')
        self.assertEqual(jsonBuf[0]['url'], 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query',
                         'URL is not from GEOFON!')

    def test_GE_geolocation(self):
        """Dataselect GE.*.*.* with latitude between -10 and 10."""
        expURL = 'http://geofon.gfz-potsdam.de/fdsnws/station/1/query'
        req = ul.Request(self.host + '?net=GE&minlat=-10&maxlat=10&service=station&format=json')
        try:
            u = ul.urlopen(req)
            buffer = u.read().decode('utf-8')
        except:
            raise Exception('Error retrieving data for GE.*.*.*')

        jsonBuf = json.loads(buffer)

        self.assertEqual(jsonBuf[0]['name'], 'station',
                         'Service of node is not station!')
        self.assertEqual(jsonBuf[0]['url'], expURL,
                         'URL is not from GEOFON!')

        queryparams = '?net={net}&sta={sta}&loc={loc}&cha={cha}&minlat=-10&maxlat=10&format=text'
        for st in jsonBuf[0]['params']:
            req = ul.Request(expURL + queryparams.format_map(st))
            try:
                u = ul.urlopen(req)
                buffer = u.read().decode('utf-8')
            except:
                raise Exception('Error retrieving GE stations with latitude between -10 and 10')

            for line in buffer.splitlines():
                if line.startswith('#'):
                    continue

                self.assertGreaterEqual(float(line.split('|')[2]), -10.0,
                                        'Latitude smaller than -10.0!')
                self.assertLessEqual(float(line.split('|')[2]), 10.0,
                                        'Latitude bigger than 10.0!')
                break



    def test_GE_geolocation_POST(self):
        """Dataselect GE.*.*.* with latitude between -10 and 10 via POST method."""
        expURL = 'http://geofon.gfz-potsdam.de/fdsnws/station/1/query'
        data = 'minlat=-10\nmaxlat=10\nservice=station\nformat=json\n\nGE * * * 1980-01-01 2018-01-01'
        req = ul.Request(self.host, data.encode('utf-8'))
        try:
            u = ul.urlopen(req)
            buffer = u.read().decode('utf-8')
        except:
            raise Exception('Error retrieving data for GE.*.*.*')

        jsonBuf = json.loads(buffer)

        self.assertEqual(jsonBuf[0]['name'], 'station',
                         'Service of node is not station!')
        self.assertEqual(jsonBuf[0]['url'], expURL,
                         'URL is not from GEOFON!')

        queryparams = '?net={net}&sta={sta}&loc={loc}&cha={cha}&start={start}&end={end}&format=text'
        for st in jsonBuf[0]['params']:
            req = ul.Request(expURL + queryparams.format_map(st))
            try:
                u = ul.urlopen(req)
                buffer = u.read().decode('utf-8')
            except:
                raise Exception('Error retrieving GE stations with latitude between -10 and 10 from the Station-WS')

            for line in buffer.splitlines():
                if line.startswith('#'):
                    continue

                self.assertGreaterEqual(float(line.split('|')[2]), -10.0,
                                        'Latitude smaller than -10.0!')
                self.assertLessEqual(float(line.split('|')[2]), 10.0,
                                        'Latitude bigger than 10.0!')
                break


    def testDS_GE_RO(self):
        """Dataselect GE,RO.*.*.* ."""
        expec = {
                 'RO': 'http://eida-sc3.infp.ro/fdsnws/dataselect/1/query',
                 'GE': 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query'
                }

        req = ul.Request(self.host + '?net=GE,RO&format=json')
        try:
            u = ul.urlopen(req)
            buffer = u.read().decode('utf-8')
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
        req = ul.Request(self.host + '?net=GE&sta=APE&format=json')
        try:
            u = ul.urlopen(req)
            buffer = u.read().decode('utf-8')
        except:
            raise Exception('Error retrieving data for GE.APE.*.*')

        jsonBuf = json.loads(buffer)

        self.assertEqual(jsonBuf[0]['name'], 'dataselect',
                         'Service of node is not dataselect!')
        self.assertEqual(jsonBuf[0]['url'], 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query',
                         'URL is not from GEOFON!')
        self.assertEqual(len(jsonBuf[0]['params']), 1,
                         'Only one set of "params" was expected!')
        self.assertEqual(jsonBuf[0]['params'][0]['sta'], 'APE',
                         'Station is not APE!')

    def testDS_CH_LIENZ_HHZ(self):
        """Dataselect CH.LIENZ.*.HHZ ."""
        req = ul.Request('%s?net=CH&sta=LIENZ&cha=HHZ&format=json' %
                              self.host)
        try:
            u = ul.urlopen(req)
            buffer = u.read().decode('utf-8')
        except:
            raise Exception('Error retrieving data for CH.LIENZ.*.HHZ')

        jsonBuf = json.loads(buffer)

        self.assertEqual(jsonBuf[0]['name'], 'dataselect',
                         'Service of node is not dataselect!')
        self.assertEqual(jsonBuf[0]['url'], 'http://eida.ethz.ch/fdsnws/dataselect/1/query',
                         'URL is not from ETH!')
        self.assertEqual(jsonBuf[0]['params'][0]['sta'], 'LIENZ',
                         'Station is not LIENZ!')
        self.assertEqual(jsonBuf[0]['params'][0]['cha'], 'HHZ',
                         'Channel is not HHZ!')

    def testDS_CH_LIENZ_BHZ(self):
        """Dataselect CH.LIENZ.*.BHZ ."""
        req = ul.Request('%s?net=CH&sta=LIENZ&cha=BHZ&format=json' %
                              self.host)
        try:
            u = ul.urlopen(req)
            buffer = u.read().decode('utf-8')
        except:
            raise Exception('Error retrieving data for CH.LIENZ.*.BHZ')

        jsonBuf = json.loads(buffer)

        self.assertEqual(jsonBuf[0]['name'], 'dataselect',
                         'Service of node is not dataselect!')
        self.assertEqual(jsonBuf[0]['url'], 'http://eida.ethz.ch/fdsnws/dataselect/1/query',
                         'URL is not from ETH!')
        self.assertEqual(jsonBuf[0]['params'][0]['sta'], 'LIENZ',
                         'Station is not LIENZ!')
        self.assertEqual(jsonBuf[0]['params'][0]['cha'], 'BHZ',
                         'Channel is not BHZ!')

    def testDS_RO_BZS_BHZ(self):
        """Dataselect RO.BZS.*.BHZ ."""
        req = ul.Request('%s?net=RO&sta=BZS&cha=BHZ&format=json' %
                              self.host)
        try:
            u = ul.urlopen(req)
            buffer = u.read().decode('utf-8')
        except:
            raise Exception('Error retrieving data for RO.BZS.*.BHZ')

        jsonBuf = json.loads(buffer)

        self.assertEqual(jsonBuf[0]['name'], 'dataselect',
                         'Service of node is not dataselect!')
        self.assertEqual(jsonBuf[0]['url'], 'http://eida-sc3.infp.ro/fdsnws/dataselect/1/query',
                         'URL is not from NIEP!')
        self.assertEqual(jsonBuf[0]['params'][0]['sta'], 'BZS',
                         'Station is not BZS!')
        self.assertEqual(jsonBuf[0]['params'][0]['cha'], 'BHZ',
                         'Channel is not BHZ!')


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
        host = configP.get('Service', 'baseURL') + '/query'
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
    # unittest.main()
