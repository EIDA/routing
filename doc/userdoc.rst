User and Operator documentation
###############################

Summary
=======

One of the aims of the
`European Integrated Data Archive <http://www.orfeus-eu.org/eida/eida.html>`_
(EIDA) is to provide transparent access and services to high quality, seismic
data across different data archives in Europe. In the context of the design
of the `EIDA New Generation` (EIDA-NG) software we envision a future in which
many different data centers offer data products using compatible types of
services, but pertaining to different seismic objects, such as waveforms,
inventory, or event data. EIDA provides one example, in which data centers
(the EIDA “nodes”) have long offered Arclink and Seedlink services, and now
offer FDSN web services, for accessing their holdings. In keeping with the
distributed nature of EIDA, these services could run at different nodes.
Depending on the type of service, these may only provide information about a
reduced subset of all the available waveforms.

To assist users to locate data, we have designed a Routing Service, which
could run at EIDA nodes or elsewhere, including on a user's personal computer.
This (meta)service is supposed to be queried by clients (or other services) in
order to localize the address(es) where the desired information is provided.

The Routing Service must serve this information in order to help the
development of smart clients and/or services of higher level, which can offer
the user an integrated view of the whole EIDA, hiding the complexity of its
internal structure. However, the Routing Service need not be aware of the
extent of the content offered by each service, avoiding the need for a large
synchronized database at any place.

The service is intended to be open and able to be queried by anyone without
the need of credentials or authentication.


Installation
============

License
-------

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Requirements
------------

 * Python 3.6+

 * mod_wsgi (if using Apache). Also Python libraries for libxslt and libxml.

.. _download:

Download
--------

Download the tar file / source from the GEOFON web page at http://geofon.gfz-potsdam.de/software.

.. note ::
    Nightly builds can be downloaded from Github (https://github.com/EIDA/routing.git).

Untar into a suitable directory visible to the web server,
such as `/var/www/eidaws/routing/1/` ::

  $ cd /var/www/eidaws/routing/1
  $ tar xvzf /path/to/tarfile.tgz

This location will depend on the location of the root (in the file system)
for your web server.

.. _oper_installation-on-uwsgi:

Installation on UWSGI
---------------------

To deploy the EIDA Routing Service on an UWSGI web server:

1. Extract the package in the desired directory.
   In these instructions we assume this directory is `/var/www/eidaws/routing/1/`.

   * If you downloaded the package from the GEOFON website, unpack the files
     into the chosen directory. (See Download_ above.)

   * If you want to get the package from Github, use the following commands: ::

       $ cd /var/www/eidaws/routing
       $ git clone https://github.com/EIDA/routing.git 1
       $ cd 1

#. Deploy UWSGI following the instructions at https://uwsgi-docs.readthedocs.io/en/latest/Install.html

   For example, for **Ubuntu/Mint** that would be ::

       $ sudo apt-get install build-essential python3
       $ sudo apt-get install apt-get install python3-dev
       $ pip3 install uwsgi

#. Change into the root directory of your installation and copy `routing.cfg.sample` to `routing.cfg`,
   or make a symbolic link ::

      $ cd /var/www/eidaws/routing/1
      $ cp routing.cfg.sample routing.cfg

#. Edit `routing.wsgi` and check that the paths there reflect the ones selected for your installation.

#. Edit `routing.cfg` and be sure to configure everything correctly. This is discussed under "`Configuration Options`_" below.

#. Start/restart the UWSGI web server ::

      $ uwsgi --http :9000 --mount /eidaws/routing/1=/var/www/eidaws/routing/1/routing.wsgi

#. Get initial metadata in the `data` directory. To do that you have to feed the system with
   some routes. Edit by hand (or copy from some other place) a file with your local
   streams and save them into `data/routing.xml`. Also the data centre information in `data/routing.json`.
   Once the file contains all routes available change into the `data` directory and run the
   ``updateAll.py`` script there. ::

      $ cd /var/www/eidaws/routing/1/data
      $ ./updateAll.py -l DEBUG

   If you don't specify any parameters to the script, the information needed will be read from
   the configuration file at the default location `../routing.cfg`. You can use the switch `-h`
   to see the parameters you can use. ::

      $ ./updateAll.py -h
      usage: updateAll.py [-h] [-l {CRITICAL,ERROR,WARNING,INFO,DEBUG}] [-s SERVER]
                          [-c CONFIG]

      Get EIDA routing configuration and "export" it to the FDSN-WS style.

      optional arguments:
        -h, --help            show this help message and exit
        -l {CRITICAL,ERROR,WARNING,INFO,DEBUG}, --loglevel {CRITICAL,ERROR,WARNING,INFO,DEBUG}
                              Verbosity in the output.
        -c CONFIG, --config CONFIG
                              Config file to use.

.. _oper_installation-on-apache:

Installation on Apache
----------------------

To deploy the EIDA Routing Service on an Apache2 web server using `mod_wsgi`:

1. Extract the package in the desired directory.
   In these instructions we assume this directory is `/var/www/eidaws/routing/1/`.

   * If you downloaded the package from the GEOFON website, unpack the files
     into the chosen directory. (See Download_ above.)

   * If you want to get the package from Github, use the following commands: ::

       $ cd /var/www/eidaws/routing
       $ git clone https://github.com/EIDA/routing.git 1
       $ cd 1

#. Enable `mod_wsgi` for Python3. For openSUSE, add 'wsgi' to the list of modules
   in the APACHE_MODULES variable in `/etc/sysconfig/apache2` ::

       APACHE_MODULES+=" python wsgi"

   and restart Apache. You should now see the following line in your
   configuration (in `/etc/apache2/sysconfig.d/loadmodule.conf` for **openSUSE**) ::

       LoadModule wsgi_module   /usr/lib64/apache2/mod_wsgi.so

   For **Ubuntu/Mint**, you can enable the module with the command ::

       $ sudo a2enmod wsgi

   and you can restart apache with::

       $ sudo service apache2 stop
       $ sudo service apache2 start


   If the module was added succesfully you should see the following two links in
   ``/etc/apache2/mods-enable`` ::

        wsgi.conf -> ../mods-available/wsgi.conf
        wsgi.load -> ../mods-available/wsgi.load

   For any distribution there may be a message like this in Apache's `error_log` file, showing
   that `mod_wsgi` was loaded ::

        [Fri Nov 29 00:08:25 2019] [notice] Apache/2.4.29 (Ubuntu)
        OpenSSL/1.1.1 mod_wsgi/4.5.17 Python/3.6 configured --
        resuming normal operations

#. Add the following lines to a new file, `conf.d/routing.conf`, or in
   `default-server.conf`, or in the configuration for your virtual host. ::

      WSGIScriptAlias /eidaws/routing/1 /var/www/eidaws/routing/1/routing.wsgi
      <Directory /var/www/eidaws/routing/1/>
          Order allow,deny
          Allow from all
      </Directory>

   Change `/var/www/eidaws/routing/1` to suit your own web server's needs.

#. Change into the root directory of your installation and copy `routing.cfg.sample` to `routing.cfg`,
   or make a symbolic link ::

      $ cd /var/www/eidaws/routing/1
      $ cp routing.cfg.sample routing.cfg

#. Edit `routing.wsgi` and check that the paths there reflect the ones selected for your installation.

#. Edit `routing.cfg` and be sure to configure everything correctly. This is discussed under "`Configuration Options`_" below.

#. Start/restart the web server e.g. as root. In **OpenSUSE** ::

      $ /etc/init.d/apache2 configtest
      $ /etc/init.d/apache2 restart

   or in **Ubuntu/Mint** ::

      $ sudo service apache2 reload
      $ sudo service apache2 stop
      $ sudo service apache2 start


#. Get initial metadata in the `data` directory. To do that you have to feed the system with
   some routes. Edit by hand (or copy from some other place) a file with your local
   streams and save them into `data/routing.xml`.
   Once the file contains all routes available change into the `data` directory and run the
   ``updateAll.py`` script there. ::

      $ cd /var/www/eidaws/routing/1/data
      $ ./updateAll.py -l DEBUG

   If you don't specify any parameters to the script, the information needed will be read from
   the configuration file at the default location `../routing.cfg`. You can use the switch `-h`
   to see the parameters you can use. ::

      $ ./updateAll.py -h
      usage: updateAll.py [-h] [-l {CRITICAL,ERROR,WARNING,INFO,DEBUG}] [-s SERVER]
                          [-c CONFIG]

      Get EIDA routing configuration and "export" it to the FDSN-WS style.

      optional arguments:
        -h, --help            show this help message and exit
        -l {CRITICAL,ERROR,WARNING,INFO,DEBUG}, --loglevel {CRITICAL,ERROR,WARNING,INFO,DEBUG}
                              Verbosity in the output.
        -c CONFIG, --config CONFIG
                              Config file to use.


#. It is important to check the permissions of the working directory
   and the files in it, as some data needs to be saved there.
   For instance, in some distributions Apache is run
   by the ``www-data`` user, which belongs to a group with the same name
   (``www-data``).
   The working directory should have read-write permission
   for the user running Apache **and** the user who will do the regular metadata updates
   (see crontab configuration in the last point of this instruction list).
   The system will also try to create and write temporary information in this directory.

   .. warning :: Wrong configuration in the permissions of the working directory could diminish the performance of the system.

   One possible configuration would be to install the system as a user (for
   instance, `sysop`), who will run the crontab update, with the working directory writable by the group of
   the user running Apache (`www-data` in **Ubuntu/Mint**). ::

    $ cd /var/www/eidaws/routing/1
    $ sudo chown -R sysop.www-data .
    $ cd data
    $ sudo chmod -R g+w .

#. Arrange for regular updates of the metadata in the working directory.
   Something like the following lines will be needed in your crontab::

    $ Daily metadata update for routing service
    52 03 * * * /var/www/eidaws/routing/1/data/updateAll.py

#. Restart the web server to apply all the changes, e.g. as root. In **OpenSUSE**::

    $ /etc/init.d/apache2 configtest
    $ /etc/init.d/apache2 restart

   or in **Ubuntu/Mint**::

    $ sudo service apache2 reload
    $ sudo service apache2 stop
    $ sudo service apache2 start


.. _configuration-options-extra:

Configuration options
^^^^^^^^^^^^^^^^^^^^^

The configuration file contains two sections up to this moment.

Service
"""""""

`baseURL` should contain the basic URL of the current Routing Service in order
to be used in the generation of the `application.wadl` method. For instance,

.. code-block:: ini

    baseURL = http://mydomain.dom/eidaws/routing/1

The variable `info` specifies the string
that the ``config`` method from the service should return.

`verbosity` controls the amount of output send to the logging system depending
of the importance of the messages. A number is expected ranging from 1 to 4,
meaning: 1: Error, 2: Warning, 3: Info and 4: Debug.

`synchronize` specifies the remote servers from which more routes should be
imported. This is explained in detail in
:ref:`Importing remote routes<importing_remote_routes>`.

`allowoverlap` determines whether the routes imported from other services can
overlap the ones already present. In case this is set to ``false`` and an
overlapping route is found, the Route will be discarded with an error message
in the log. When it is set to ``true``, the Route will be still included, but
the resulting data could be inconsistent.

.. _service_configuration:

.. code-block:: ini

    [Service]
    baseURL = http://mydomain.dom/eidaws/routing/1
    info = Routing information from the Arclink Server at GEOFON.
       All the routes related to EIDA are supposed to be available here.
    verbosity = 3
    synchronize = SERVER2, http://server2/eidaws/routing/1
        SERVER3, http://server3/eidaws/routing/1
    allowoverlap = true

Installation problems
^^^^^^^^^^^^^^^^^^^^^

Always check your web server log files (e.g. for Apache: ``access_log`` and
``error_log``) for clues.

If you visit http://localhost/eidaws/routing/1/version on your machine
you should see the version information of the deployed service ::

    1.2.3

If this information cannot be retrieved, the installation was not successful.
If this **do** show up, check that the information there looks correct.

Testing the service
-------------------

Two scripts are provided to test the functionality of the service at different
levels. These can be found in the ``test`` folder under the root directory of
your installation.

Class level
^^^^^^^^^^^

The script called ``testRoute.py`` will try to import the objects used in the
Routing Service in order to test their functionality. The data will not be
provided by the web service, but from the classes inside the package. In this
way, the logic of the package and the coherence of the information can be
tested, excluding other factors related to the configuration of other pieces
of software (f.i. web server, firewall, etc.). ::

    $ ./testRoute.py
    Running test...
    Checking Dataselect CH.LIENZ.*.BHZ... [OK]
    Checking Dataselect CH.LIENZ.*.HHZ... [OK]
    Checking Dataselect CH.LIENZ.*.?HZ... [OK]
    Checking Dataselect GE.*.*.*... [OK]
    Checking Dataselect GE.APE.*.*... [OK]
    Checking Dataselect RO.BZS.*.BHZ... [OK]

A set of test cases have been implemented and the expected responses are
compared with the ones returned by the service.

.. note:: The test cases are related to the sample routing data which is
          provided in routing.xml.sample and will make no sense if the service
          is configured to route other set of networks. In that case, the
          operator of the service should modify scripts in order to test the
          coherence of the information provided by the service.

Service level
^^^^^^^^^^^^^

The script called ``testService.py`` will try to connect to a Routing Service
at a particular URL, which **must** be passed as a parameter. In previous
versions the default value was http://localhost/eidaws/routing/1/query, but as
the functionality of the Routing Service was much improved, real and resolvable
addresses are needed. ::

    $ ./testService.py http://server/path/query
    Running test...
    Checking Dataselect CH.LIENZ.*.BHZ... [OK]
    Checking Dataselect CH.LIENZ.*.HHZ... [OK]
    Checking Dataselect CH.LIENZ.*.?HZ... [OK]
    Checking Dataselect GE.*.*.*... [OK]
    Checking Dataselect GE.APE.*.*... [OK]
    Checking Dataselect GE,RO.*.*.*... [OK]
    Checking Dataselect RO.BZS.*.BHZ... [OK]
    Checking non-existing network XX... [OK]
    Checking incompatibility between alternative=true and format=get... [OK]
    Checking the 'application.wadl' method... [OK]
    Checking the 'info' method... [OK]
    Checking very large URI... [OK]
    Checking the 'version' method... [OK]
    Checking wrong values in alternative parameter... [OK]
    Checking swap start and end time... [OK]
    Checking wrong format option... [OK]
    Checking unknown parameter... [OK]

The set of test cases related to data consistency are the same as in the
``testRoute.py`` script. The other tests are related to the protocol itself.

Maintenance
-----------

The Routing Table needs to be updated regularly due to the small but constant
changes in the EIDA structure. You should always be able to run safely the
``updateAll.py`` script at any time you want.
The Routing Service creates a binary version of the XML containing the routes,
but this will be automatically updated each time a new inventory XML file is
detected.

Upgrade
-------

At this stage, it's better to back up and then remove the old installation
first. ::

    $ cd /var/www/eidaws/routing/ ; mv 1 1.old

Then reinstall from scratch, as in the :ref:`installation instructions <oper_installation-on-apache>`.
Your web server configuration should need no modification.
At Steps 4-6, re-use your previous versions of ``routing.wsgi`` and ``routing.cfg`` ::

    $ cp ../1.old/routing.wsgi routing.wsgi
    $ cp ../1.old/routing.cfg routing.cfg

And of course, copy your local routing table also. ::

    $ cp ../1.old/data/routing.xml data/routing.xml


Using the Service
=================

Default configuration
---------------------

A script called ``updateAll.py`` is provided in the package, which can be
found in the ``data`` folder. This script can load the local routing information
as well as synchronize the remote routes, which are provided by the other EIDA
nodes. All necessary parameters will be read from the configuration file
(``routing.cfg``). Namely, the list of data centres, which have data to
synchronize.

When the service starts, checks if there is a file called ``routing.xml`` in
the ``data`` directory. This file is expected to contain all the information
needed to feed the routing table. The file format must be Arclink-XML.

The following is an example of an Arclink-XML file.

.. code-block:: xml

    <?xml version="1.0" encoding="utf-8"?>
    <ns0:routing xmlns:ns0="http://server/ns/Routing/1.0/">
        <ns0:route networkCode="GE" stationCode="" locationCode="" streamCode="">
          <ns0:station address="http://domain/fdsnws/station/1/query"
              priority="1" start="1993-01-01T00:00:00" end="" />
          <ns0:dataselect address="http://domain/fdsnws/dataselect/1/query"
              priority="1" start="1993-01-01T00:00:00" end="" />
        </ns0:route>
        <ns0:route networkCode="CH" stationCode="*" locationCode="*" streamCode="*">
          <ns0:station address="http://domain2/fdsnws/station/1/query"
              priority="1" start="1980-01-01T00:00:00" end="" />
          <ns0:dataselect address="http://domain2/fdsnws/dataselect/1/query"
              priority="1" start="1980-01-01T00:00:00" end="" />
        </ns0:route>
    </ns0:routing>

This is exactly the file that the ``updateAll.py`` script creates
with information from EIDA. With this information and
the metadata downloaded by the same script the service can be started.

Manual configuration
--------------------

A better option would be to take the file from Arclink as a base and make some
adjustments to it manually. The number of routes could be reduced drastically
by means of a clever use of the wildcards.


.. _importing_remote_routes:

Importing remote routes
-----------------------

In the case case that one datacenter decides to include routes from other
datacenter (as in the EIDA case) , there is no need to define them locally.

A normal use case would be that the datacenter `A` needs to provide routing
information of data centres `A` **and** `B` to its users. In order to allow
datacenter `B` to export its routes, a method called ``localconfig`` is
defined. This method will return to the caller all the routing information
locally defined in the ``routing.xml`` file. Every datacenter is free to
restrict the access to this method to well-known IP addresses or to keep it
completely open by means of access rules in the web server.

If the datacenter `A` has access to this method, it can import the routes
automatically by means of the inclusion of the base URL of the service at
datacenter `B` in the *synchronize* option (under *Service*) of its
configuration file.

.. code-block:: ini

    [Service]
    synchronize = DC-B, http://datacenter-b/path/routing/1

When the service in datacenter `A` starts, it will first include all the
routes defined in ``routing.xml`` and then it will save the routes read from
http://datacenter-b/path/routing/1/localconfig in a file called ``DC-B.xml``
under the ``data`` folder. This file can be used for future reference in case
that all the routes need to be updated and datacenter `B` is not available.

Once the file is saved, all the routes inside it will be added to the routing
table in memory.

.. _station_caching:

Cache of station names and locations
------------------------------------

Once all the routes have been imported, all instances of Station-WS are queried
with the available routes in order to get a list of stations and their
locations. The main purpose of this is to improve the querying capabilities of
the Routing Service in the following two use cases.

  * Locations will be used to allow the usage of the FDSN parameters: `minlat`,
    `maxlat`, `minlon`, and `maxlon`. These can be used to define a rectangular
    area and **discover** all stations present. This functionality was not
    possible with the previous version of the Service, as no information
    related to the streams was saved.

  * The case where the station names are needed is quite different. It had been
    detected that some queries contained the station name (e.g. sta=XYZ) but no
    information about the network. This could be usual when a user remembers
    the name of the station, which is associated with a location or village,
    but does not pay attention to the network to which it belongs. As many
    routes have a configuration like NETCODE.*.*.*, there was no way to know
    if the station belonged to that network or not. Meaning that in most of the
    cases, this resulted in the Routing Service sending the user almost **all**
    the available routes to further discover where the station is. This type of
    routes are very practical for the Administrator of the service, but less
    useful for the user in cases like this. The solution was to create an
    automatic cache of the station names, so that the Administrator can still
    configure very short routes, while the user can use more precise filters in
    his/her request.

.. _virtual_networks:

Defining virtual networks
-------------------------

.. warning: This functionality has been just recently added and, therefore, not
            tested as thoroughly as the rest of the code in the system. Feel
            free to use it, but consider it in an **alpha** status.

The concept of a collection of stations, different of the formal network, has
existed since a long time. There are many reasons why this could result
interesting. From creating a virtual network code which encompasses many
networks, to defining a subset of stations from one or more networks.

Since version 1.1.0 this new feature is supported in a way that the operator
can define in the `routing.xml` file a virtual network code as a list of
stations.

For instance, an example is shown below where the _VN network is defined as the
combination of stations ST1, ST2 from network RN1 and ST3 from network RN2.

.. code-block:: xml

    <?xml version="1.0" encoding="utf-8"?>
    <ns0:routing xmlns:ns0="http://geofon.gfz-potsdam.de/ns/Routing/1.0/">
      <ns0:vnetwork networkCode="_VN">
        <ns0:stream networkCode="RN1" stationCode="ST1" locationCode="*" streamCode="*"
          start="2015-01-01T00:00:00" end="2015-12-31T00:00:00" />
        <ns0:stream networkCode="RN1" stationCode="ST2" locationCode="*" streamCode="*"
          start="2015-01-01T00:00:00" end="2015-12-31T00:00:00" />
        <ns0:stream networkCode="RN2" stationCode="ST3" locationCode="*" streamCode="*"
          start="2015-01-01T00:00:00" end="2015-12-31T00:00:00" />
      </ns0:vnetwork>
    </ns0:routing>

In the case that the synchronization is enabled, the virtual networks will also
be synchronized and shared with the other Routing services. They will be treated
in the same way as routes. Collisions with remote definitions will be checked
and will not be allowed.

The most important point to clarify when using virtual networks in the query is
that the Routing Service will **always return real network and stations codes**.
In this way, the returned codes can be always used with the downstream services,
which most probably will not support virtual network codes, or at least it is
not clear that will contain exactly the same definitions of the virtual
networks.


Methods available
-----------------

Description of the service
^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``application.wadl`` method returns a WADL (web application description
layer) description of the interface using the MIME type
`application/xml`. Any parameters submitted to the method will be ignored. The
WADL describes all parameters supported by this implementation and can be used
as an automatic way to determine methods and parameters supported by this
service. This information is generated on the fly.

Version of the software
^^^^^^^^^^^^^^^^^^^^^^^

The ``version`` method returns the implementation version as a simple text
string using the MIME type `text/plain`. Any parameters submitted to the method
will be ignored. This scheme follows the FDSN web services approach.

The service is versioned according the following three-digit (x.y.z) pattern: ::

   SpecMajor.SpecMinor.Implementation


where the fields have the following meaning:

 #. `SpecMajor`: The major specification version, all implementations sharing
    this `SpecMajor` value will be backwards compatible with all prior releases.
    Values are integers starting at 1.
 #. `SpecMinor`: The minor specification version, incremented when optional
    parameters or behavior is added to the previous specification but backwards
    compatibility is maintained with the previous major versions, i.e. all
    1.y.z service versions will be compatible with version 1.0. Values are
    integers starting at 0.
 #. `Implementation`: The implementation version, an integer identifier
    specific to the data center implementation. Useful to track service updates
    for bug fixes, etc. but with no implication on conformance to the
    specification.

Together the `SpecMajor` and `SpecMinor` versions imply a minimum expected
behavior of a given service. This versioning scheme allows clients to expect
specific behavior based on the `SpecMajor` version, while allowing the extension
of the service with optional parameters and maintaining backwards compatibility.
Each version number is service specific, there is no implication that
`SpecMajor` version numbers across services (from EIDA or FDSN) are related.

Endpoints from which data have been imported
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``endpoints`` method returns a list of URLs pointing to the Routing Services (or static file) from the endpoints, which contribute with routes for this Routing Service. The MIME type of the returned value is
`text/plain`.

Exporting routes
^^^^^^^^^^^^^^^^

The ``localconfig`` method reads the content of the ``routing.xml`` file and
returns it when this method is invoked. The MIME type of the returned value is
`text/xml`.

.. seealso:: :ref:`Importing remote routes <importing_remote_routes>`

The ``globalconfig`` method reads all available routes and exports them to a JSON schema which has been approved by the FDSN. The MIME type of the returned value is
`application/json`.



Querying information
^^^^^^^^^^^^^^^^^^^^

The ``query`` method is how the users access the main functionality of the
service. Both ``GET`` and ``POST`` methods must be supported.

Input parameters
""""""""""""""""

The complete list of input parameters can be seen in :ref:`Table 2.1<Table_2.1>`.
Parameter names must be in lowercase, and may be abbreviated as shown, following
the FDSN style. Valid input values must have the format shown in the “Format”
column. All the values passed as parameters will be case-insensitive strings
composed of numbers and letters. No other symbols will be allowed with the
exception of:

* wildcards ("``*``" and "``?``"), which may be used to select the streams (for
  parameters `network`, `station`, `location` and `channel` only), and
* the symbols specified in the ISO 8601 format for dates, namely ‘:’, "``-``"
  (minus) and "``.``" may be used for the `starttime` and `endtime` parameters,
* the string "``--``"  (two minus symbols) may appear for the location
  parameter only.

Wildcards are accepted in the case of `network`, `station`, `location` and
`channel`. The character ``*`` matches any value, while ``?`` matches any
character. For any of these parameters, if no value is given it will be set to
a star (``*``).

Any of these four parameters may also be submitted as comma-separated lists in
order to select two or more values with a single request. For example, the
`channel` parameter may be used to specify multiple channels: ::

    channel=LHE,LHN,LHZ,BHZ (the individual values may also include wildcards)

Blank or empty `location` identifiers may be specified as "``--``" (two dashes)
if needed, which the service must translate to an empty string.

.. _Table_2.1:

.. tabularcolumns:: |l|l|l|p{8cm}|c|
.. table:: Input parameters description

 ================= ======== ======== ================================ ==========
 Parameter         Support  Format   Description                      Default
 ================= ======== ======== ================================ ==========
 starttime (start) Required ISO 8601 Limit results to time series
                                     samples on or
                                     after the specified start
                                     time.                            Any
 endtime (end)     Required ISO 8601 Limit results to time series
                                     samples on or before the
                                     specified end time.              Any
 network (net)     Required char     Select one network code.
                                     This can be either SEED
                                     network codes or data center
                                     defined codes.                   ``*``
 station (sta)     Required char     Select one station code.         ``*``
 location (loc)    Required char     Select one location
                                     identifier. As a special
                                     case “--” (two dashes) will
                                     be translated to an empty
                                     string to match blank
                                     location IDs.                    ``*``
 channel (cha)     Required char     Select one channel code.         ``*``
 minlatitude       Required float    Limit to stations with a
 (minlat)                            latitude larger than or equal
                                     to the specified minimum.        ``-90``
 maxlatitude       Required float    Limit to stations with a
 (maxlat)                            latitude smaller than or equal
                                     to the specified maximum.        ``90``
 minlongitude      Required float    Limit to stations with a
 (minlon)                            longitude larger than or equal
                                     to the specified minimum.        ``-180``
 maxlongitude      Required float    Limit to stations with a
 (maxlon)                            longitude smaller than or equal
                                     to the specified maximum.        ``180``
 service           Required char     Specify which service will
                                     be queried (arclink,
                                     seedlink, station,
                                     dataselect).                     dataselect
 format            Required char     Select the output format.
                                     Valid values are: xml, json,
                                     get, post                        xml
 alternative       Optional boolean  Specify if the alternative
                                     routes should be also
                                     included in the answer.
                                     Accepted values are “true”
                                     and “false”.                     false
 ================= ======== ======== ================================ ==========


Output description and format
"""""""""""""""""""""""""""""

There are four different output formats supported by this service. The
structure of the information returned is different with each format type. In
case of a successful request the HTTP status code will be ``200``, and the
response will be as described below for each format.

XML format
""""""""""

This is the default selection if the parameter `format` is not specified or if
it is given with the value ``xml``. The MIME type must be set to `text/xml`.
The following is an example of the expected XML structure. Each datacenter
element must contain exactly one url element, specifying the URL of the
service at a given data centre, exactly one name element, which gives the name
of the service a list of params elements, each describing a stream, or set of
streams by using appropriate wildcarding, available using the service at that
URL. The params element may be repeated as many times as necessary inside the
datacenter element.

.. code-block:: xml

 <service>
    <datacenter>
        <url>http://ws.resif.fr/fdsnws/dataselect/1/query</url>
        <params>
            <loc>*</loc>
            <end/>
            <sta>KES28</sta>
            <cha>*</cha>
            <start/>
            <net>4C</net>
        </params>
        <name>dataselect</name>
    </datacenter>
 </service>

JSON format
"""""""""""

if the format parameter is ``json``, the information will be returned with
MIME type `application/json`. The content will be a JSON (JavaScript Object
notation) array, in which each element is a JSON object corresponding to a
``<datacenter>`` element in the XML format shown above. For the example
response above, this would appear as:

.. code-block:: json

 [{"url": "http://ws.resif.fr/fdsnws/dataselect/1/query",
 "params": [{"loc": "*", "end": "", "sta": "KES28", "cha": "*", "start": "",
             "net": "4C"}], "name": "dataselect"}]

It should be noted that the value associated with params is an array of
objects and that there will be as many objects as needed for the same
datacenter.

GET format
""""""""""

When the `format` parameter is set to ``get``, the output will be declared as
`text/plain` and will consist of one URL per line. The URLs will be constructed
in a way that they can be used directly by the client to request the necessary
information without the need to parse them. ::

 http://ws.resif.fr/fdsnws/dataselect/1/query?sta=KES28&net=4C&
     start=2010-01-01T00:00:00&end=2010-01-01T00:10:00


POST format
"""""""""""

If `format` is ``post``, the output will be also declared as `text/plain` and
the structure will consist of:
* a line with a URL where the request must be made,
* a list of lines with the format declared in the FDSN Web Services
specification to do a POST request.

If the request should be split in more than one datacenter, the blocks for
every datacenter will be separated by a blank line and the structure will be
repeated (URL and POST body). ::

 http://ws.resif.fr/fdsnws/dataselect/1/query
 4C KES28 * * 2010-01-01T00:00:00 2010-01-01T00:10:00

Alternative routes
""""""""""""""""""

.. warning:: As a rule of a thumb and in a normal case, the alternative
             addresses should only be used if there is no response from the
             authoritative data center.

If the `alternative` parameter is set, the service will return all the routes
that match the requested criteria without paying attention to the priority.
The client will be required to interpret the priority of the routes and to
select the combination of routes that best fits their needs to request the
information. The client needs also to take care of checking the information to
detect overlapping routes, which will definitely occur when a primary and an
alternative route are being reported for the same stream.

.. note:: It should be noted that the benefits of the "get" and "post" format
          outputs are almost nonexistent if alternative routes are included in
          the output, since the result should be parsed in order to operate on
          the different routes.

How to pass the parameters
""""""""""""""""""""""""""

In the case of performing a request via the ``GET`` method, the parameters
must be given in the usual way. Namely, ::

 http://server_url?key1=value1&key2=value2

But in the case that the parameters should be passed via a ``POST`` method,
the following format is expected. The first lines can be used to pass the
parameters not related to streams or timewindows (service, format, alternative)
with one key=value clause per line. For instance, ::

 service=station

For the six parameters used to select streams and timewindows, one stream/
timewindow pair is expected per line and the format must be: ::

 net sta loc cha start end

If there is no defined time window, an empty string should be given as '' or "".

.. warning:: The separation of a request in more than one URL/parameters can be
             avoided by a client who performs an expansion of the wildcards
             before contacting this service. However, in some complex cases it
             could also happen that a stream is stored in two different data
             centers depending on the time window. In this case, it is
             unavoidable to split the request in more than one data center.

Abnormal responses
""""""""""""""""""

In addition to a ``200 OK`` status code for a successful request, other
responses are possible, as shown in the :ref:`Table 2.2`. These are essentially
the same as for FDSN web services. Under error, maintenance or other unusual
conditions a client may receive other HTTP codes generated by web service
containers, and other intermediate web technology.

.. _Table 2.2:

.. table:: HTTP status codes returned by the Routing service

 ===== =======================================================================
 Code  Description
 ===== =======================================================================
 200    OK, Successful request, results follow.
 204    Request was properly formatted and submitted but no data matches the
        selection.
 400    Bad request due to improper specification, unrecognized parameter,
        parameter value out of range, etc.
 413    Request would result in too much data being returned or the request
        itself is too large. Returned error
        message should include the service limitations in the detailed
        description. Service limits should
        also be documented in the service WADL.
 414    Request URI too large
 500    Internal server error
 503    Service temporarily unavailable, used in maintenance and error
        conditions
 ===== =======================================================================

Information about the content of service
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When the method `info` is invoked a description about the information handled
by the Routing Service should be returned. The answer must be of MIME type
`text/plain` and actually is a text-free output. However, in the first lines
it is expected to be specified which information can we find by querying the
service. For instance, ::

 All Networks from XYZ institution
 Stations in Indonesia
 Stations in San Francisco

 Other comments and descriptions that could be of interest of the user.

Any parameter passed to this method will be ignored.

