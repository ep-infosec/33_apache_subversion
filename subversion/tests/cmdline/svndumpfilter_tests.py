#!/usr/bin/env python
#
#  svndumpfilter_tests.py:  testing the 'svndumpfilter' tool.
#
#  Subversion is a tool for revision control.
#  See https://subversion.apache.org for more information.
#
# ====================================================================
#    Licensed to the Apache Software Foundation (ASF) under one
#    or more contributor license agreements.  See the NOTICE file
#    distributed with this work for additional information
#    regarding copyright ownership.  The ASF licenses this file
#    to you under the Apache License, Version 2.0 (the
#    "License"); you may not use this file except in compliance
#    with the License.  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing,
#    software distributed under the License is distributed on an
#    "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#    KIND, either express or implied.  See the License for the
#    specific language governing permissions and limitations
#    under the License.
######################################################################

# General modules
import os
import sys
import tempfile

# Our testing module
import svntest
from svntest.verify import SVNExpectedStdout, SVNExpectedStderr

# Get some helper routines
from svnadmin_tests import load_and_verify_dumpstream, load_dumpstream
from svntest.main import run_svn, run_svnadmin

# (abbreviation)
Skip = svntest.testcase.Skip_deco
SkipUnless = svntest.testcase.SkipUnless_deco
XFail = svntest.testcase.XFail_deco
Issues = svntest.testcase.Issues_deco
Issue = svntest.testcase.Issue_deco
Wimp = svntest.testcase.Wimp_deco
Item = svntest.wc.StateItem


######################################################################
# Helper routines


def filter_and_return_output(dump, bufsize=0, *varargs):
  """Filter the array of lines passed in 'dump' and return the output
  and errput"""

  if isinstance(dump, str):
    dump = [ dump ]

  # Does the caller want the stderr?
  if '-q' in varargs or '--quiet' in varargs:
      expected_errput = None # Stderr with -q or --quiet is a real error!
  else:
      expected_errput = svntest.verify.AnyOutput
  ## TODO: Should we handle exit_code?
  exit_code, output, errput = svntest.main.run_command_stdin(
    svntest.main.svndumpfilter_binary, expected_errput, bufsize, True,
    dump, *varargs)

  # Since we call svntest.main.run_command_stdin() in binary mode,
  # normalize the stderr line endings on Windows ourselves.
  if sys.platform == 'win32':
    errput = [x.replace('\r\n', '\n') for x in errput]

  return output, errput


######################################################################
# Tests

@Issue(2982)
def reflect_dropped_renumbered_revs(sbox):
  "reflect dropped renumbered revs in svn:mergeinfo"

  ## See https://issues.apache.org/jira/browse/SVN-2982. ##

  # Test svndumpfilter with include option
  sbox.build(empty=True)
  dumpfile_location = os.path.join(os.path.dirname(sys.argv[0]),
                                   'svndumpfilter_tests_data',
                                   'with_merges.dump')
  dumpfile = svntest.actions.load_dumpfile(dumpfile_location)

  filtered_out, filtered_err = filter_and_return_output(
      dumpfile, 0, "include",
      "trunk", "branch1",
      "--skip-missing-merge-sources",
      "--drop-empty-revs",
      "--renumber-revs", "--quiet")

  load_dumpstream(sbox, filtered_out, "--ignore-uuid")

  # Verify the svn:mergeinfo properties
  url = sbox.repo_url
  expected_output = svntest.verify.UnorderedOutput([
    url + "/trunk - /branch1:4-5\n",
    ])
  svntest.actions.run_and_verify_svn(expected_output, [],
                                     'propget', 'svn:mergeinfo', '-R',
                                     sbox.repo_url)


  # Test svndumpfilter with exclude option
  sbox.build(empty=True)
  filtered_out, filtered_err = filter_and_return_output(
      dumpfile, 0, "exclude", "branch1",
      "--skip-missing-merge-sources",
      "--drop-empty-revs",
      "--renumber-revs", "--quiet")

  load_dumpstream(sbox, filtered_out, "--ignore-uuid")

  # Verify the svn:mergeinfo properties
  expected_output = svntest.verify.UnorderedOutput([
    url + "/trunk - \n",
    ])
  svntest.actions.run_and_verify_svn(expected_output, [],
                                     'propget', 'svn:mergeinfo', '-R',
                                     sbox.repo_url)

@Issue(3181)
def svndumpfilter_loses_mergeinfo(sbox):
  "svndumpfilter loses mergeinfo"
  #svndumpfilter loses mergeinfo if invoked without --renumber-revs

  ## See https://issues.apache.org/jira/browse/SVN-3181. ##

  sbox.build(empty=True)
  dumpfile_location = os.path.join(os.path.dirname(sys.argv[0]),
                                   'svndumpfilter_tests_data',
                                   'with_merges.dump')
  dumpfile = svntest.actions.load_dumpfile(dumpfile_location)

  filtered_out, filtered_err = filter_and_return_output(dumpfile, 0, "include",
                                                        "trunk", "branch1",
                                                        "--quiet")
  load_dumpstream(sbox, filtered_out)

  # Verify the svn:mergeinfo properties
  url = sbox.repo_url
  expected_output = svntest.verify.UnorderedOutput([
    url + "/trunk - /branch1:4-8\n",
    ])
  svntest.actions.run_and_verify_svn(expected_output, [],
                                     'propget', 'svn:mergeinfo', '-R',
                                     sbox.repo_url)


def _simple_dumpfilter_test(sbox, dumpfile, *dumpargs):
  """Run svndumpfilter with arguments DUMPARGS, taking input from DUMPFILE.
     Check that the output consists of the standard Greek tree excluding
     all paths that start with 'A/B/E', 'A/D/G' or 'A/D/H'."""
  wc_dir = sbox.wc_dir

  filtered_output, filtered_err = filter_and_return_output(dumpfile, 0,
                                                           '--quiet',
                                                           *dumpargs)

  # Setup our expectations
  load_dumpstream(sbox, filtered_output, '--ignore-uuid')
  expected_disk = svntest.main.greek_state.copy()
  expected_disk.remove('A/B/E/alpha')
  expected_disk.remove('A/B/E/beta')
  expected_disk.remove('A/B/E')
  expected_disk.remove('A/D/H/chi')
  expected_disk.remove('A/D/H/psi')
  expected_disk.remove('A/D/H/omega')
  expected_disk.remove('A/D/H')
  expected_disk.remove('A/D/G/pi')
  expected_disk.remove('A/D/G/rho')
  expected_disk.remove('A/D/G/tau')
  expected_disk.remove('A/D/G')

  expected_output = svntest.wc.State(wc_dir, {
    'A'           : Item(status='A '),
    'A/B'         : Item(status='A '),
    'A/B/lambda'  : Item(status='A '),
    'A/B/F'       : Item(status='A '),
    'A/mu'        : Item(status='A '),
    'A/C'         : Item(status='A '),
    'A/D'         : Item(status='A '),
    'A/D/gamma'   : Item(status='A '),
    'iota'        : Item(status='A '),
    })

  expected_status = svntest.actions.get_virginal_state(wc_dir, 1)
  expected_status.remove('A/B/E/alpha')
  expected_status.remove('A/B/E/beta')
  expected_status.remove('A/B/E')
  expected_status.remove('A/D/H/chi')
  expected_status.remove('A/D/H/psi')
  expected_status.remove('A/D/H/omega')
  expected_status.remove('A/D/H')
  expected_status.remove('A/D/G/pi')
  expected_status.remove('A/D/G/rho')
  expected_status.remove('A/D/G/tau')
  expected_status.remove('A/D/G')

  # Check that our paths really were excluded
  svntest.actions.run_and_verify_update(wc_dir,
                                        expected_output,
                                        expected_disk,
                                        expected_status)


@Issue(2697)
def dumpfilter_with_targets(sbox):
  "svndumpfilter --targets blah"
  ## See https://issues.apache.org/jira/browse/SVN-2697. ##

  sbox.build(empty=True)

  dumpfile_location = os.path.join(os.path.dirname(sys.argv[0]),
                                   'svndumpfilter_tests_data',
                                   'greek_tree.dump')
  dumpfile = svntest.actions.load_dumpfile(dumpfile_location)

  (fd, targets_file) = tempfile.mkstemp(dir=svntest.main.temp_dir)
  try:
    targets = open(targets_file, 'w')
    targets.write('/A/D/H\n')
    targets.write('/A/D/G\n')
    targets.close()
    _simple_dumpfilter_test(sbox, dumpfile,
                            'exclude', '/A/B/E', '--targets', targets_file)
  finally:
    os.close(fd)
    os.remove(targets_file)


def dumpfilter_with_patterns(sbox):
  "svndumpfilter --pattern PATH_PREFIX"

  sbox.build(empty=True)

  dumpfile_location = os.path.join(os.path.dirname(sys.argv[0]),
                                   'svndumpfilter_tests_data',
                                   'greek_tree.dump')
  dumpfile = svntest.actions.load_dumpfile(dumpfile_location)
  _simple_dumpfilter_test(sbox, dumpfile,
                          'exclude', '--pattern', '/A/D/[GH]*', '/A/[B]/E*')

#----------------------------------------------------------------------
# More testing for issue #3020 'Reflect dropped/renumbered revisions in
# svn:mergeinfo data during svnadmin load'
#
# Specifically, test that svndumpfilter, when used with the
# --skip-missing-merge-sources option, removes mergeinfo that refers to
# revisions that are older than the oldest revision in the dump stream.
@Issue(3020)
def filter_mergeinfo_revs_outside_of_dump_stream(sbox):
  "filter mergeinfo revs outside of dump stream"

  sbox.build(empty=True)

  # Load a partial dump into an existing repository.
  #
  # Picture == 1k words:
  #
  # The dump file we filter in this test, 'mergeinfo_included_partial.dump', is
  # a dump of r6:HEAD of the following repos:
  #
  #                       __________________________________________
  #                      |                                         |
  #                      |             ____________________________|_____
  #                      |            |                            |     |
  # trunk---r2---r3-----r5---r6-------r8---r9--------------->      |     |
  #   r1             |        |     |       |                      |     |
  # initial          |        |     |       |______                |     |
  # import         copy       |   copy             |            merge   merge
  #                  |        |     |            merge           (r5)   (r8)
  #                  |        |     |            (r9)              |     |
  #                  |        |     |              |               |     |
  #                  |        |     V              V               |     |
  #                  |        | branches/B2-------r11---r12---->   |     |
  #                  |        |     r7              |____|         |     |
  #                  |        |                        |           |     |
  #                  |      merge                      |___        |     |
  #                  |      (r6)                           |       |     |
  #                  |        |_________________           |       |     |
  #                  |                          |        merge     |     |
  #                  |                          |      (r11-12)    |     |
  #                  |                          |          |       |     |
  #                  V                          V          V       |     |
  #              branches/B1-------------------r10--------r13-->   |     |
  #                  r4                                            |     |
  #                   |                                            V     V
  #                  branches/B1/B/E------------------------------r14---r15->
  #
  #
  # The mergeinfo on the complete repos would look like this:
  #
  #   Properties on 'branches/B1':
  #     svn:mergeinfo
  #       /branches/B2:11-12
  #       /trunk:6,9
  #   Properties on 'branches/B1/B/E':
  #     svn:mergeinfo
  #       /branches/B2/B/E:11-12
  #       /trunk/B/E:5-6,8-9
  #   Properties on 'branches/B2':
  #     svn:mergeinfo
  #       /trunk:9
  #
  # We will run the partial dump through svndumpfilter using the the
  # --skip-missing-merge-soruces which should strip out any revisions < 6.
  # Then we'll load the filtered result into an empty repository.  This
  # should offset the incoming mergeinfo by -5.  In addition, any mergeinfo
  # referring to the initial revision in the dump file (r6) should be
  # removed because the change it refers to (r5:6) is not wholly within the
  # dumpfile.  The resulting mergeinfo should look like this:
  #
  #   Properties on 'branches/B1':
  #     svn:mergeinfo
  #       /branches/B2:6-7
  #       /trunk:4
  #   Properties on 'branches/B1/B/E':
  #     svn:mergeinfo
  #       /branches/B2/B/E:6-7
  #       /trunk/B/E:3-4
  #   Properties on 'branches/B2':
  #     svn:mergeinfo
  #       /trunk:4
  partial_dump = os.path.join(os.path.dirname(sys.argv[0]),
                                   'svndumpfilter_tests_data',
                                   'mergeinfo_included_partial.dump')
  partial_dump_contents = svntest.actions.load_dumpfile(partial_dump)
  filtered_dumpfile2, filtered_out = filter_and_return_output(
      partial_dump_contents,
      8192, # Set a sufficiently large bufsize to avoid a deadlock
      "include", "trunk", "branches",
      "--skip-missing-merge-sources",
      "--quiet")
  load_dumpstream(sbox, filtered_dumpfile2, '--ignore-uuid')
  # Check the resulting mergeinfo.
  url = sbox.repo_url + "/branches"
  expected_output = svntest.verify.UnorderedOutput([
    url + "/B1 - /branches/B2:6-7\n",
    "/trunk:4\n",
    url + "/B2 - /trunk:4\n",
    url + "/B1/B/E - /branches/B2/B/E:6-7\n",
    "/trunk/B/E:3-4\n"])
  svntest.actions.run_and_verify_svn(expected_output, [],
                                     'propget', 'svn:mergeinfo', '-R',
                                     sbox.repo_url)

  # Blow away the current repos, create an empty one in its place, and
  # then load this skeleton repos into the empty target:
  #
  #   Projects/       (Added r1)
  #     README        (Added r2)
  #     Project-X     (Added r3)
  #     Project-Y     (Added r4)
  #     Project-Z     (Added r5)
  #     docs/         (Added r6)
  #       README      (Added r6).
  sbox.build(empty=True)
  skeleton_location = os.path.join(os.path.dirname(sys.argv[0]),
                                                  'svnadmin_tests_data',
                                                  'skeleton_repos.dump')
  skeleton_dumpfile = svntest.actions.load_dumpfile(skeleton_location)
  load_dumpstream(sbox, skeleton_dumpfile, '--ignore-uuid')
  partial_dump2 = os.path.join(os.path.dirname(sys.argv[0]),
                                   'svndumpfilter_tests_data',
                                   'mergeinfo_included_partial.dump')
  partial_dump_contents2 = svntest.actions.load_dumpfile(partial_dump2)
  # Now use the partial dump file we used above, but this time exclude
  # the B2 branch.  Load the filtered dump into the /Projects/Project-X
  # subtree of the skeleton repos.
  filtered_dumpfile2, filtered_err = filter_and_return_output(
      partial_dump_contents2,
      8192, # Set a sufficiently large bufsize to avoid a deadlock
      "exclude", "branches/B2",
      "--skip-missing-merge-sources",
      "--drop-empty-revs",
      "--renumber-revs")

  # Starting with the same expectation we had when loading into an empty
  # repository, adjust each revision by +6 to account for the six revision
  # already present in the target repos, that gives:
  #
  #   Properties on 'branches/B1':
  #     svn:mergeinfo
  #       /branches/B2:12-13
  #       /trunk:10
  #   Properties on 'branches/B1/B/E':
  #     svn:mergeinfo
  #       /branches/B2/B/E:12-13
  #       /trunk/B/E:9-10
  #   Properties on 'branches/B2':
  #     svn:mergeinfo
  #       /trunk:10
  #
  # ...But /branches/B2 has been filtered out, so all references to
  # that branch should be gone, leaving:
  #
  #   Properties on 'branches/B1':
  #     svn:mergeinfo
  #       /trunk:10
  #   Properties on 'branches/B1/B/E':
  #     svn:mergeinfo
  #       /trunk/B/E:9-10
  #
  # ...But wait, there's more!  Because we use the '--drop-empty-revs'
  # option, when filtering out 'branches/B2' all the revisions that effect
  # only that branch should be dropped (i.e. original revs r7, r11, and r12).
  # In and of itself that has no effect, but we also specifiy the
  # '--renumber-revs' option, so when r7 is dropped, r8 should map to r7,
  # r9 to r8, and r10 to r9 (and so on).  That should finally leave us with:
  #
  #   Properties on 'branches/B1':
  #     svn:mergeinfo
  #       /trunk:9
  #   Properties on 'branches/B1/B/E':
  #     svn:mergeinfo
  #       /trunk/B/E:8-9
  #
  # This test currently fails with this mergeinfo:
  #
  #
  #
  #
  # Check that all the blather above really happens.  First does
  # svndumpfilter report what we expect to stderr?
  expected_err = [
      "Excluding (and dropping empty revisions for) prefixes:\n",
      "   '/branches/B2'\n",
      "\n",
      "Revision 6 committed as 6.\n",
      "Revision 7 skipped.\n",        # <-- DROP!
      "Revision 8 committed as 7.\n",
      "Revision 9 committed as 8.\n",
      "Revision 10 committed as 9.\n",
      "Revision 11 skipped.\n",       # <-- DROP!
      "Revision 12 skipped.\n",       # <-- DROP!
      "Revision 13 committed as 10.\n",
      "Revision 14 committed as 11.\n",
      "Revision 15 committed as 12.\n",
      "\n",
      "Dropped 3 revisions.\n",
      "\n",
      "Revisions renumbered as follows:\n",
      "   15 => 12\n",
      "   14 => 11\n",
      "   13 => 10\n",
      "   12 => (dropped)\n", # <-- DROP!
      "   11 => (dropped)\n", # <-- DROP!
      "   10 => 9\n",
      "   9 => 8\n",
      "   8 => 7\n",
      "   7 => (dropped)\n",  # <-- DROP!
      "   6 => 6\n",
      "\n",
      "Dropped 2 nodes:\n",
      "   '/branches/B2'\n",
      "   '/branches/B2/D/H/chi'\n",
      "\n"]
  svntest.verify.verify_outputs(
      "Actual svndumpfilter stderr does not agree with expected stderr",
      None, filtered_err, None, expected_err)

  # Now actually load the filtered dump into the skeleton repository
  # and then check the resulting mergeinfo.
  load_dumpstream(sbox, filtered_dumpfile2,
                  '--parent-dir', '/Projects/Project-X', '--ignore-uuid')

  url = sbox.repo_url + "/Projects/Project-X/branches"
  expected_output = svntest.verify.UnorderedOutput([
    url + "/B1 - /Projects/Project-X/trunk:9\n",
    url + "/B1/B/E - /Projects/Project-X/trunk/B/E:8-9\n"])
  svntest.actions.run_and_verify_svn(expected_output, [],
                                     'propget', 'svn:mergeinfo', '-R',
                                     sbox.repo_url)

#----------------------------------------------------------------------
# More testing for issue #3020 'Reflect dropped/renumbered revisions in
# svn:mergeinfo data during svnadmin load'
#
# Using svndumpfilter with the --drop-empty-revs option, but without the
# --renumber-revs option, can create a dump with non-contiguous revisions.
# Such dumps should not interfere with the correct remapping of mergeinfo
# source revisions.
@Issue(3020)
def dropped_but_not_renumbered_empty_revs(sbox):
  "mergeinfo maps correctly when dropping revs"

  sbox.build(empty=True)

  # The dump file mergeinfo_included_full.dump represents this repository:
  #
  #
  #                       __________________________________________
  #                      |                                         |
  #                      |             ____________________________|_____
  #                      |            |                            |     |
  # trunk---r2---r3-----r5---r6-------r8---r9--------------->      |     |
  #   r1             |        |     |       |                      |     |
  # initial          |        |     |       |______                |     |
  # import         copy       |   copy             |            merge   merge
  #                  |        |     |            merge           (r5)   (r8)
  #                  |        |     |            (r9)              |     |
  #                  |        |     |              |               |     |
  #                  |        |     V              V               |     |
  #                  |        | branches/B2-------r11---r12---->   |     |
  #                  |        |     r7              |____|         |     |
  #                  |        |                        |           |     |
  #                  |      merge                      |___        |     |
  #                  |      (r6)                           |       |     |
  #                  |        |_________________           |       |     |
  #                  |                          |        merge     |     |
  #                  |                          |      (r11-12)    |     |
  #                  |                          |          |       |     |
  #                  V                          V          V       |     |
  #              branches/B1-------------------r10--------r13-->   |     |
  #                  r4                                            |     |
  #                   |                                            V     V
  #                  branches/B1/B/E------------------------------r14---r15->
  #
  #
  # The mergeinfo on mergeinfo_included_full.dump is:
  #
  #   Properties on 'branches/B1':
  #     svn:mergeinfo
  #       /branches/B2:11-12
  #       /trunk:6,9
  #   Properties on 'branches/B1/B/E':
  #     svn:mergeinfo
  #       /branches/B2/B/E:11-12
  #       /trunk/B/E:5-6,8-9
  #   Properties on 'branches/B2':
  #     svn:mergeinfo
  #       /trunk:9
  #
  # Use svndumpfilter to filter mergeinfo_included_full.dump, excluding
  # branches/B2, while dropping, but not renumbering, empty revisions.
  #
  # Load the filtered dump into an empty repository.  Since we are excluding
  # /branches/B2 and dropping empty revs, revisions 7, 11, and 12 won't be
  # included in the filtered dump.
  full_dump = os.path.join(os.path.dirname(sys.argv[0]),
                                   'svnadmin_tests_data',
                                   'mergeinfo_included_full.dump')
  full_dump_contents = svntest.actions.load_dumpfile(full_dump)
  filtered_dumpfile, filtered_out = filter_and_return_output(
      full_dump_contents,
      16384, # Set a sufficiently large bufsize to avoid a deadlock
      "exclude", "branches/B2",
      "--skip-missing-merge-sources", "--drop-empty-revs")

  # Now load the filtered dump into an empty repository.
  load_dumpstream(sbox, filtered_dumpfile, '--ignore-uuid')

  # The mergeinfo in the newly loaded repos should have no references to the
  # dropped branch and the remaining merge source revs should be remapped to
  # reflect the fact that the loaded repository no longer has any empty
  # revisions:
  #
  #   Properties on 'branches/B1':
  #     svn:mergeinfo
  #       /trunk:6,8
  #                ^
  #       With r7 dropped, r9 in the incoming
  #       dump becomes r8 in the loaded repos.
  #
  #   Properties on 'branches/B1/B/E':
  #     svn:mergeinfo
  #       /trunk/B/E:5-8
  #                    ^
  #       With r7 dropped, r8 and r9 in the incoming
  #       dump becomes r7 and r8 in the loaded repos.

  # Check the resulting mergeinfo.
  url = sbox.repo_url + "/branches"
  expected_output = svntest.verify.UnorderedOutput([
    url + "/B1 - /trunk:6,8\n",
    url + "/B1/B/E - /trunk/B/E:5-8\n"])
  svntest.actions.run_and_verify_svn(expected_output, [],
                                     'propget', 'svn:mergeinfo', '-R',
                                     sbox.repo_url)

#----------------------------------------------------------------------
def match_empty_prefix(sbox):
  "svndumpfilter with an empty prefix"

  dumpfile_location = os.path.join(os.path.dirname(sys.argv[0]),
                                   'svndumpfilter_tests_data',
                                   'greek_tree.dump')
  dumpfile = svntest.actions.load_dumpfile(dumpfile_location)

  def test(sbox, dumpfile, *dumpargs):
    """Run svndumpfilter with DUMPFILE as the input lines, load
       the result and check it matches EXPECTED_DISK, EXPECTED_OUTPUT,
       EXPECTED_STATUS."""

    # Filter the Greek tree dump
    filtered_output, filtered_err = filter_and_return_output(dumpfile, 0,
                                                             '--quiet',
                                                             *dumpargs)
    if filtered_err:
      raise SVNExpectedStderr(filtered_err)

    # Load the filtered dump into a repo and check the result
    sbox.build(empty=True)
    load_dumpstream(sbox, filtered_output, '--ignore-uuid')
    svntest.actions.run_and_verify_update(sbox.wc_dir,
                                          expected_output,
                                          expected_disk,
                                          expected_status)

  # Test excluding everything
  expected_disk = svntest.wc.State(sbox.wc_dir, {})
  expected_output = svntest.wc.State(sbox.wc_dir, {})
  expected_status = svntest.wc.State(sbox.wc_dir, {
                      '': Item(status='  ', wc_rev=1) })

  test(sbox, dumpfile, 'exclude', '')

  # Test including everything
  expected_disk = svntest.main.greek_state.copy()
  expected_output = svntest.main.greek_state.copy().tweak(status='A ')
  expected_status = svntest.actions.get_virginal_state(sbox.wc_dir, 1)

  test(sbox, dumpfile, 'include', '', '/A/D/G')

  # Note: We also ought to test the '--pattern' option, including or
  # excluding a pattern of '*'.  However, passing a wildcard parameter
  # is troublesome on Windows: it may be expanded, depending on whether
  # the svndumpfilter executable was linked with 'setargv.obj', and there
  # doesn't seem to be a consistent way to quote such an argument to
  # prevent expansion.

@Issue(2760)
def accepts_deltas(sbox):
  "accepts deltas in the input"
  # Accept format v3 (as created by 'svnadmin --deltas' or svnrdump).

  sbox.build(empty=True)
  dumpfile_location = os.path.join(os.path.dirname(sys.argv[0]),
                                   'svndumpfilter_tests_data',
                                   'simple_v3.dump')
  dump_in = svntest.actions.load_dumpfile(dumpfile_location)

  dump_out, err = filter_and_return_output(dump_in, 0, "include",
                                                        "trunk", "--quiet")

  expected_revs = [
    svntest.wc.State('', {
      'trunk'     : svntest.wc.StateItem(props={'soup': 'No soup for you!'}),
      'trunk/foo' : svntest.wc.StateItem("This is file 'foo'.\n"),
      }),
    svntest.wc.State('', {
      'trunk'     : svntest.wc.StateItem(props={'soup': 'No soup for you!'}),
      'trunk/foo' : svntest.wc.StateItem("This is file 'foo'.\n"),
      }),
    svntest.wc.State('', {
      'trunk'     : svntest.wc.StateItem(props={'story': 'Yada yada yada...'}),
      'trunk/foo' : svntest.wc.StateItem("This is file 'foo'.\n"),
      }),
    ]

  load_and_verify_dumpstream(sbox, [], [], expected_revs, True, dump_out,
                             '--ignore-uuid')



@Issue(4234)
def dumpfilter_targets_expect_leading_slash_prefixes(sbox):
  "dumpfilter targets expect leading '/' in prefixes"
  ## See https://issues.apache.org/jira/browse/SVN-4234. ##

  sbox.build(empty=True)

  dumpfile_location = os.path.join(os.path.dirname(sys.argv[0]),
                                   'svndumpfilter_tests_data',
                                   'greek_tree.dump')
  dumpfile = svntest.actions.load_dumpfile(dumpfile_location)

  (fd, targets_file) = tempfile.mkstemp(dir=svntest.main.temp_dir)
  try:
    targets = open(targets_file, 'w')

    # Removing the leading slash in path prefixes should work.
    targets.write('A/D/H\n')
    targets.write('A/D/G\n')
    targets.close()
    _simple_dumpfilter_test(sbox, dumpfile,
                            'exclude', '/A/B/E', '--targets', targets_file)
  finally:
    os.close(fd)
    os.remove(targets_file)

@Issue(3681)
def drop_all_empty_revisions(sbox):
  "drop all empty revisions except revision 0"

  dumpfile_location = os.path.join(os.path.dirname(sys.argv[0]),
                                   'svndumpfilter_tests_data',
                                   'empty_revisions.dump')
  dump_contents = svntest.actions.load_dumpfile(dumpfile_location)

  filtered_dumpfile, filtered_err = filter_and_return_output(
      dump_contents,
      8192, # Set a sufficiently large bufsize to avoid a deadlock
      "include", "branch1",
      "--drop-all-empty-revs")

  expected_err = [
       "Including (and dropping empty revisions for) prefixes:\n",
       "   '/branch1'\n",
       "\n",
       "Revision 0 committed as 0.\n",
       "Revision 1 skipped.\n",
       "Revision 2 committed as 2.\n",
       "Revision 3 skipped.\n",
       "\n",
       "Dropped 2 revisions.\n",
       "\n"]

  svntest.verify.verify_outputs(
      "Actual svndumpfilter stderr does not agree with expected stderr",
      None, filtered_err, None, expected_err)

  # Test with --renumber-revs option.
  filtered_dumpfile, filtered_err = filter_and_return_output(
      dump_contents,
      8192, # Set a sufficiently large bufsize to avoid a deadlock
      "include", "branch1",
      "--drop-all-empty-revs",
      "--renumber-revs")

  expected_err = [
       "Including (and dropping empty revisions for) prefixes:\n",
       "   '/branch1'\n",
       "\n",
       "Revision 0 committed as 0.\n",
       "Revision 1 skipped.\n",
       "Revision 2 committed as 1.\n",
       "Revision 3 skipped.\n",
       "\n",
       "Dropped 2 revisions.\n",
       "\n",
       "Revisions renumbered as follows:\n",
       "   3 => (dropped)\n",
       "   2 => 1\n",
       "   1 => (dropped)\n",
       "   0 => 0\n",
       "\n"]

  svntest.verify.verify_outputs(
      "Actual svndumpfilter stderr does not agree with expected stderr",
      None, filtered_err, None, expected_err)


########################################################################
# Run the tests


# list all tests here, starting with None:
test_list = [ None,
              reflect_dropped_renumbered_revs,
              svndumpfilter_loses_mergeinfo,
              dumpfilter_with_targets,
              dumpfilter_with_patterns,
              filter_mergeinfo_revs_outside_of_dump_stream,
              dropped_but_not_renumbered_empty_revs,
              match_empty_prefix,
              accepts_deltas,
              dumpfilter_targets_expect_leading_slash_prefixes,
              drop_all_empty_revisions,
              ]

if __name__ == '__main__':
  svntest.main.run_tests(test_list)
  # NOTREACHED


### End of file.
