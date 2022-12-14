#
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

__all__ = [ ]

import sys
if sys.hexversion < 0x3000000:
  sys.stderr.write('[SKIPPED] at least Python 3.0 is required\n')
  # Yes, it really is required: some tests will FAIL under Python 2 but PASS
  # under Python 3.  See, for example,
  # https://issues.apache.org/jira/browse/SVN-4891?focusedCommentId=17518154#comment-17518154

  # note: exiting is a bit harsh for a library module, but we really do
  # require Python 3.0. this package isn't going to work otherwise.

  # we're skipping this test, not failing, so exit with 0
  sys.exit(0)

try:
  import sqlite3
except ImportError:
  sys.stderr.write('[SKIPPED] Python sqlite3 module required\n')
  sys.exit(0)

# don't export this name
del sys

class Failure(Exception):
  'Base class for exceptions that indicate test failure'
  pass

class Skip(Exception):
  'Base class for exceptions that indicate test was skipped'
  pass

# import in a specific order: things with the fewest circular imports first.
from . import testcase
from . import wc
from . import verify
from . import tree
from . import sandbox
from . import main
from . import actions
from . import factory
