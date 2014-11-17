Routing Service v1.0

Installation
============

The installation instructions are included in the package, but need first to be
generated. Follow the instructions in the next section to do it.

Documentation
=============

To get the documentation of the current version of the Routing Service you
please follow these steps:

1) Go to the "doc" subdirectory located where the package was decompressed.
Let's suppose it is "/var/www/eidaws/routing/1".

$ cd /var/www/eidaws/routing/1/doc

2) Build the documentation.

$ make latexpdf

3) Open the generated PDF file with an appropriate application (e.g. acroread,
evince, etc). The file will be located under the .build/latex directory.

$ acroread .build/latex/Routing-WS.pdf

Copy this file to the location most suitable to you for future use.
