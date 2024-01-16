#
# Routing Service
#
# 2014-2023 Helmholtz Centre Potsdam GFZ German Research Centre for Geosciences, Potsdam, Germany
#
# ----------------------------------------------------------------------

import sys
import os

directory = os.path.dirname(__file__)

sys.path.append(directory)
import routing

application = routing.application
