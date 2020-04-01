#
# Routing Service
#
# 2014-2020 Javier Quinteros, Deutsches GFZ Potsdam <javier@gfz-potsdam.de>
#
# ----------------------------------------------------------------------

import sys
import os

directory = os.path.dirname(__file__)

sys.path.append(directory)
import routing

application = routing.application
