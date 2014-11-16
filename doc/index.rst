.. Routing-WS documentation master file, created by
   sphinx-quickstart on Wed Oct  1 16:09:29 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Routing-WS's documentation!
======================================

.. toctree::
   :maxdepth: 2

Installation
============

Requirements
------------

 * Python 2.7
   
 * mod_wsgi (if using Apache). Also Python libraries for libxslt and libxml.

 * The ``update-metadata.sh`` script uses `wget`.

.. _download:

Download
--------

Download the tar file / source from the GEOFON web page at http://geofon.gfz-potsdam.de/software.
[Eventually it may be included in the SeisComP distribution.]

.. note ::
    Nightly builds can be downloaded from Bitbucket. You can request access at geofon_dc@gfz-potsdam.de.

Untar into a suitable directory visible to the web server,
such as `/var/www/eidaws/routing/1/` ::

  cd /var/www/eidaws/routing/1
  tar xvzf /path/to/tarfile.tgz

This location will depend on the location of the root (in the file system)
 for your web server.

.. _oper_installation-on-apache:

Installation on Apache
----------------------

To deploy the EIDA Routing Service on an Apache2 web server using `mod_wsgi`:

 0. Unpack the files into the chosen directory.
    (See Download_ above.)
    In these instructions we assume this directory is `/var/www/eidaws/routing/1/`.

 #. Enable `mod_wsgi`. For openSUSE, add 'wsgi' to the list of modules in the APACHE_MODULES variable in `/etc/sysconfig/apache2` ::

       APACHE_MODULES+=" python wsgi"

    and restart Apache. You should now see the following line in your
    configuration (in `/etc/apache2/sysconfig.d/loadmodule.conf` for **openSUSE**) ::

        LoadModule wsgi_module   /usr/lib64/apache2/mod_wsgi.so

    You can also look at the output from ``a2enmod -l`` - you should see wsgi listed.

    For **Ubuntu/Mint**, you can enable the module with the command ::

        sudo a2enmod wsgi

    and you can restart apache with::

        sudo service apache2 stop
        sudo service apache2 start

    If the module was added succesfully you should see the following two links in
    ``/etc/apache2/mods-enable`` ::

        wsgi.conf -> ../mods-available/wsgi.conf
        wsgi.load -> ../mods-available/wsgi.load

    For any distribution there may be a message like this in Apache's `error_log` file, showing
    that `mod_wsgi` was loaded ::

        [Tue Jul 16 14:24:32 2013] [notice] Apache/2.2.17 (Linux/SUSE)
        PHP/5.3.5 mod_python/3.3.1 Python/2.7 mod_wsgi/3.3 configured
         -- resuming normal operations


 #. Add the following lines to a new file, `conf.d/routing.conf`, or in
    `default-server.conf`, or in the configuration for your virtual host ::

     WSGIScriptAlias /eidaws/routing/1 /var/www/eidaws/routing/1/routing.wsgi
        <Directory /var/www/eidaws/routing/1/>
            Order allow,deny
            Allow from all
        </Directory>

    Change `/var/www/eidaws/routing/1` to suit your own web server's needs.

 #. Copy `routing.cfg.sample` to `routing.cfg`,
    or make a symbolic link ::

      cp routing.cfg.sample routing.cfg

 #. Edit `routing.cfg` and be sure to configure everything corectly. This is discussed under "`Configuration Options`_" below.

 #. Start/restart the web server e.g. as root. In **OpenSUSE** ::

      # /etc/init.d/apache2 configtest
      # /etc/init.d/apache2 restart

    or in **Ubuntu/Mint** ::

      # sudo service apache2 reload
      # sudo service apache2 stop
      # sudo service apache2 start


 #. Get initial metadata in the `data` directory by running the ``update-metadata.sh`` script in that directory. ::

      # cd /var/www/eidaws/routing/1/data
      # ./update-metadata.sh

 #. It is important to check the permissions of the working directory
    and the files in it, as some data needs to be saved there.
    For instance, in some distributions Apache is run
    by the ``www-data`` user, which belongs to a group with the same name
    (``www-data``).
    The working directory should have read-write permission
    for the user running Apache **and** the user who will do the regular metadata updates
    (see crontab configuration in the last point of this instruction list).
    The system will also try to create and
    write temporary information in this directory.
   
    .. warning :: Wrong configuration in the permissions of the working directory could diminish the performance of the system.

    One possible configuration would be to install the system as a user (for
    instance, `sysop`), who will run the crontab update, with the working directory writable by the group of
    the user running Apache (`www-data` in **Ubuntu/Mint**). ::

    # cd {top directory}
    # sudo chown -R sysop.www-data .
    # cd data
    # sudo chmod -R g+w .

 #. Arrange for regular updates of the metadata in the working directory.
    Something like the following lines will be needed in your crontab ::

    # Daily metadata update for routing service
    52 03 * * * /var/www/eidaws/routing/1/data/update-metadata.sh

.. _configuration-options-extra:

Configuration options
^^^^^^^^^^^^^^^^^^^^^

The configuration file contains two sections up to this moment.

Arclink
"""""""

In the Arclink section an arclink server must be defined, from which the
default routing table should be retrieved.
The default value is the Arclink server running at GEOFON, but this can be
configured with the address of any Arclink server. ::

    [Arclink]
    server = eida.gfz-potsdam.de
    port = 18002

Service
"""""""

This section contains three variables. The variable *info* specifies the string
that the *config* method from the service should return.
The variable *updateTime* determines at which moment of the day should be
updated all the routing information.
The format for the update time should be *HH:MM* separated by a space. It is
not necessary that the different time entries are in order. If no update is
required, there should be nothing at the right side of the *=* character.

*verbosity* controls the amount of output send to the logging system depending
of the importance of the messages. The levels are: 1) Error, 2) Warning, 3)
Info and 4) Debug. ::

    [Service]
    info = Routing information from the Arclink Server at GEOFON
    updateTime = 23:01 22:05 21:58
    verbosity = 3

Installation problems
^^^^^^^^^^^^^^^^^^^^^

Always check your web server log files (e.g. for Apache: `access_log` and
`error_log`) for clues.

If you visit http://localhost/eidaws/routing/1/version on your machine
you should see the version information of the deployed service ::

    1.0.0

If these information cannot be retrieved, the installation was not successfull.
If they *do* show up, check that the information there looks correct.

Testing the service
-------------------

Two scripts are provided to test the functionality of the service at different
levels.

Class level
^^^^^^^^^^^

The script called *testRoute.py* will try to import the objects used in the
Routing Service in order to test their functionality. The data will not be
provided by the web service, but from the classes inside the package. In this
way, the logic of the package and teh coherence of the information can be
tested, excluding other factors related to the configuration of other pieces
of software (f.i. web server, firewall, etc.). ::

    ./testRoute.py
    Running test...
    Checking Dataselect CH.LIENZ.*.BHZ... [OK]
    Checking Dataselect CH.LIENZ.*.HHZ... [OK]
    Checking Dataselect CH.LIENZ.*.?HZ... [OK]
    Checking Dataselect GE.*.*.*... [OK]
    Checking Dataselect GE.APE.*.*... [OK]
    Checking Dataselect RO.BZS.*.BHZ... [OK]

Service level
^^^^^^^^^^^^^

The script called *testService.py* will try to connect a Routing Service at
a particular URL, which can be passed as a parameter. The default value will
test the service at: http://localhost/eidaws/routing/1/query, what can be
used to check the local installation. ::

    ./testService.py -u http://server/path/query
    Running test...
    Checking Dataselect CH.LIENZ.*.BHZ... [OK]
    Checking Dataselect CH.LIENZ.*.HHZ... [OK]
    Checking Dataselect CH.LIENZ.*.?HZ... [OK]
    Checking Dataselect GE.*.*.*... [OK]
    Checking Dataselect GE.APE.*.*... [OK]
    Checking Dataselect RO.BZS.*.BHZ... [OK]
    
A set of test cases have been implemented and the expected responses are
compared with the ones returned by the service.


Maintenance
-----------

Metadata needs to be updated regularly due to the small but constant changes in
the Arclink inventory. You can always run safely the ``update-metadata.sh``
script at any time you want.
The Routing Service creates a processed version of the Arclink XML, but this
will be automatically updated each time a new inventory XML file is detected.

Upgrade
-------

At this stage, it's best to back up and then remove the old installation
first. ::

    cd /var/www/eidaws/routing/ ; mv 1 1.old

Then reinstall from scratch, as in the :ref:`installation instructions <oper_installation-on-apache>`.
Your web server configuration should need no modification.
At Steps 4-6, re-use your previous versions of ``routing.wsgi`` and ``routing.cfg`` ::

    cp ../1.old/routing.wsgi routing.wsgi
    cp ../1.old/routing.cfg routing.cfg


Using the Service
=================

Default configuration
---------------------

The RoutingCache class includes a method called *configArclink*, that retrieves
the routing information for EIDA from an Arclink Server. The address and port
of the server are the ones specified in the configuration file.

When the service starts, it checks if there is a file called *routing.xml* in
the *data* directory. This file is expected to contain all the information
needed to feed the routing table. The file must be in an Arclink-XML format.

The following is an example of an Arclink-XML file. ::

    <?xml version="1.0" encoding="utf-8"?>
    <ns0:routing xmlns:ns0="http://server/ns/Routing/1.0/">
        <ns0:route locationCode="" networkCode="BE" stationCode="" streamCode="">
            <ns0:arclink address="bhlsa02.knmi.nl:18002" end="" priority="1"
                start="1980-01-01T00:00:00.0000Z" />
        </ns0:route>
        <ns0:route locationCode="" networkCode="BA" stationCode="" streamCode="">
            <ns0:arclink address="eida.rm.ingv.it:18002" end="" priority="1"
                start="1980-01-01T00:00:00.0000Z" />
            <ns0:seedlink address="eida.rm.ingv.it:18000" priority="1" />
        </ns0:route>
    </ns0:routing>

If the file is not present, *configArclink* is called and the file is created
with the information provided by the Arclink server. With this information and the metadata
downloaded by ``update_metadata.sh`` the service can be provided.

Manual configuration
--------------------

A better option would be to create the file manually, taking the one obtained
from Arclink as a base. The number of routes could be reduced drastically by
means of a clever use of the wildcards.

If some extra information not available within EIDA would like to be also
routed, there is a *masterTable* that can be used. If the service finds a file
called *masterTable.xml* when it starts, these routes are loaded in a separate
table and are given the maximum priority. Only the network will be used when
a request is processed. This could be perfect to route request to other
networks, whose internal structure is not well known.

In the following example, we show how to route to the service from IRIS, when
the *II* network is requested. ::

    <?xml version="1.0" encoding="utf-8"?>
    <ns0:routing xmlns:ns0="http://geofon.gfz-potsdam.de/ns/Routing/1.0/">
        <ns0:route locationCode="" networkCode="II" stationCode="" streamCode="">
            <ns0:dataselect address="service.iris.edu/fdsnws/dataselect/1/query"
                end="" priority="9" start="1980-01-01T00:00:00.0000Z" />
        </ns0:route>
    </ns0:routing>

.. warning:: The *priority* attribute will be valid only in the context of the
             masterTable. There is no relation with the priority for a similar
             route that could be in the normal routing table.

The routes that are part of the *masterTable.xml* will not be sent when the
*localconfig* method of the service is called, only the ones in the normal
routing table.

The aim is that the routes in the normal routing table are the ones that should
be synchronized with other Routing Services.

.. todo:: EL OTRO METODO!



Documentation for developers
============================

Definition of the classes
-------------------------

.. automodule:: utils

RoutingCache class
------------------

.. autoclass:: utils.RoutingCache
   :members:
   :undoc-members:

Route class
-----------

.. autoclass:: utils.Route
   :members:
   :undoc-members:

Stream class
------------

.. autoclass:: utils.Stream
   :members:
   :undoc-members:

TW (timewindow)  class
----------------------

.. autoclass:: utils.TW
   :members:
   :undoc-members:

RouteMT class
-------------

.. autoclass:: utils.RouteMT
   :members:
   :undoc-members:

RequestMerge class
------------------

.. autoclass:: utils.RequestMerge
   :members:
   :undoc-members:

InventoryCache class
--------------------

.. autoclass:: inventorycache.InventoryCache
   :members:
   :undoc-members:

.. Indices and tables
   ==================
   * :ref:`genindex`
   * :ref:`modindex`
   * :ref:`search`
