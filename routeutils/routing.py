#!/usr/bin/env python

"""Routing Webservice for EIDA

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

import datetime
import xml.etree.cElementTree as ET
import json
from wsgicomm import WIClientError
from utils import RequestMerge


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
    """Convert a list with dictionaries to an XML ElementTree Element.

    :param listdict: Dictionaries
    :type listdict: list
    :returns: XML Tree with the dictionaries received as parameter.
    :rtype: xml.etree.cElementTree.Element
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
    """Iterator providing NSLC tuples from comma separated components.

    :param net: Network code(s) in comma-separated format.
    :type net: list
    :param sta: Station code(s) in comma-separated format.
    :type sta: list
    :param loc: Location code(s) in comma-separated format.
    :type loc: list
    :param cha: Channel code(s) in comma-separated format.
    :type cha: list
    :rtype: tuple
    :returns: NSLC tuples
    """
    for n in net:
        for s in sta:
            for l in loc:
                for c in cha:
                    yield (n, s, l, c)


def applyFormat(resultRM, outFormat='xml'):
    """Apply the format specified to the RequestMerge object received.

    :param resultRM: List with the result of a query.
    :type resultRM: RequestMerge
    :param outFormat: Output format for the result.
    :type outFormat: string
    :rtype: string
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
                # All parameters are passed in the GET format with exception of
                # priority which is consumed here.
                iterObj.append(datacenter['url'] + '?' +
                               '&'.join([k + '=' + (str(item[k]) if not
                                         isinstance(item[k], datetime.datetime)
                                         else item[k].isoformat()) for k in
                                         item if item[k] not in ('', '*') and
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
                        (isinstance(item['end'], basestring) and
                         not len(item['end']))):
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
