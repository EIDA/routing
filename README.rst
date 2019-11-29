Routing Service v1.2
--------------------

Why a Routing Service?
======================

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
synchronised database at any place.

The service is intended to be open and able to be queried by anyone without
the need of credentials or authentication.

License
=======

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

Installation
============

The installation instructions are included in the package, but need first to be
generated. Follow the instructions in the next section to do it.

Documentation
=============

To get the documentation of the current version of the Routing Service you
please follow these steps:

1. Go to the "doc" subdirectory located where the package was decompressed.
Let's suppose it is "/var/www/eidaws/routing/1". ::

  $ cd /var/www/eidaws/routing/1/doc

2. Build the
documentation. ::

  $ make latexpdf

3. Open the generated PDF file with an appropriate application (e.g. acroread,
evince, etc). The file will be located under the .build/latex directory. ::

  $ acroread .build/latex/Routing-WS.pdf

Copy this file to the location most suitable to you for future use.
