#!/usr/bin/env python

"""Routing Webservice for EIDA

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

   :Copyright:
       2014-2016 Javier Quinteros, GEOFON, GFZ Potsdam <geofon@gfz-potsdam.de>
   :License:
       GPLv3
   :Platform:
       Linux

.. moduleauthor:: Javier Quinteros <javier@gfz-potsdam.de>, GEOFON, GFZ Potsdam
"""

import os
import cgi
import datetime
import xml.etree.cElementTree as ET
import json
from wsgicomm import WIContentError
from wsgicomm import WIClientError
from wsgicomm import WIURIError
from wsgicomm import WIError
from wsgicomm import send_plain_response
from wsgicomm import send_xml_response
from wsgicomm import send_error_response
import logging
from utils import RequestMerge
from utils import RoutingCache
from utils import RoutingException

try:
    import configparser
except ImportError:
    import ConfigParser as configparser


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


# Important to support the comma-syntax from FDSN (f.i. GE,RO,XX)
def lsNSLC(net, sta, loc, cha):
    for n in net:
        for s in sta:
            for l in loc:
                for c in cha:
                    yield (n, s, l, c)


def applyFormat(resultRM, outFormat='xml'):
    """Apply the format specified to the RequestMerge object received.

    :rtype: str
    :returns: Transformed version of the input in the desired format
    """

    if not isinstance(resultRM, RequestMerge):
        raise Exception('applyFormat expects a RequestMerge object!')

    if outFormat == 'json':
        iterObj = json.dumps(resultRM, default=datetime.datetime.isoformat)
        return iterObj
    elif outFormat == 'get':
        iterObj = []
        for datacenter in resultRM:
            for item in datacenter['params']:
                iterObj.append(datacenter['url'] + '?' +
                               '&'.join([k + '=' + (str(item[k]) if
                                         type(item[k]) is not
                                         type(datetime.datetime.now())
                                         else item[k].isoformat()) for k in item
                                         if item[k] not in ('', '*') and
                                         k != 'priority']))
        iterObj = '\n'.join(iterObj)
        return iterObj
    elif outFormat == 'post':
        iterObj = []
        for datacenter in resultRM:
            iterObj.append(datacenter['url'])
            for item in datacenter['params']:
                item['loc'] = item['loc'] if len(item['loc']) else '--'
                item['start'] = item['start'] if isinstance(item['start'],
                                                            basestring) \
                    else item['start'].isoformat()

                # If endtime is a datetime get it in isoformat (string)
                if isinstance(item['end'], datetime.datetime):
                    item['end'] = item['end'].isoformat()
                # If endtime is not a string use a default value (tomorrow)
                if ((not isinstance(item['end'], basestring)) or
                    (isinstance(item['end'], basestring) and not len(item['end']))):
                    item['end'] = (datetime.date.today() +
                                   datetime.timedelta(days=1)).isoformat()
                iterObj.append(item['net'] + ' ' + item['sta'] + ' ' +
                               item['loc'] + ' ' + item['cha'] + ' ' +
                               item['start'] + ' ' + item['end'])
            iterObj.append('')
        iterObj = '\n'.join(iterObj)
        return iterObj
    elif outFormat == 'xml':
        iterObj2 = ET.tostring(ConvertDictToXml(resultRM))
        return iterObj2
    else:
        raise WIClientError('Wrong format requested!')
