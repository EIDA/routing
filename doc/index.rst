.. Routing-WS documentation master file, created by
   sphinx-quickstart on Wed Oct  1 16:09:29 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Routing-WS's documentation!
======================================

.. toctree::
   :maxdepth: 2

Installation and use
====================

Requirements
------------

 * SeisComP(reg) 3 provides useful functions for configuration, geometry, travel time computation.
   If you use the :program:`update-metadata.sh` script, you will need :program:`arclink_fetch`, either included in the SeisComP distribution, or standalone [http://www.seiscomp3.org/wiki/doc/applications/arclink_fetch].

 * Seiscomp Python library (`$SEISCOMP_ROOT/lib/python/seiscomp`), including a
   recent version of `manager.py`
   (SeisComP 3 release >= 2013.200; there is a temporary version with this
   release in the `tools` directory, which you can use to replace your
   installed version in `$SEISCOMP_ROOT/lib/python/seiscomp/arclink`).

 * Python, mod_wsgi (if using Apache). Also Python libraries for libxslt and libxml.

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
    You may also need to add a section like ::

        <Directory /var/www/eidaws/routing/1/>
            Order allow,deny
            Allow from all
        </Directory>

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

      # cd /var/www/eidaws/routing/1
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
    # sudo chmod -R g+w .

 #. Arrange for regular updates of the metadata in the working directory.
    Something like the following lines will be needed in your crontab ::

    # Daily metadata update for routing service
    52 03 * * * /var/www/eidaws/routing/1/update-metadata.sh

Installation problems
~~~~~~~~~~~~~~~~~~~~~

Always check your web server log files (e.g. for Apache: `access_log` and
`error_log`) for clues.

If you visit http://localhost/eidaws/routing/1/version on your machine
you should see the version information of the deployed service ::

    1.0.0

If these information cannot be retrieved, the installation was not successfull.
If they *do* show up, check that the information there looks correct.

.. _configuration-options-extra:

Configuration options
~~~~~~~~~~~~~~~~~~~~~

The configuration file contains only a couple of variables up to this moment.
Namely, the Arclink server where the default routing table should be retrieved.
the default value is the Arclink server running at GEOFON, but this can be
configured with the address of any Arclink server. ::

    [Arclink]
    server = eida.gfz-potsdam.de
    port = 18002

Maintenance
~~~~~~~~~~~

Metadata may need updating after changes in Arclink inventory - you
can safely run the ``update-metadata.sh`` script at any time to do that.
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


Documentation for developers
============================

Routing module
--------------

.. automodule:: routing

RoutingCache class
------------------

.. autoclass:: routing.RoutingCache
   :members:
   :undoc-members:

Route class
-----------

.. autoclass:: routing.Route
   :members:
   :undoc-members:

Stream class
------------

.. autoclass:: routing.Stream
   :members:
   :undoc-members:

RouteMT class
-------------

.. autoclass:: routing.RouteMT
   :members:
   :undoc-members:

RequestMerge class
------------------

.. autoclass:: routing.RequestMerge
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

