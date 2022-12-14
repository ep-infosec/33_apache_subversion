#!/usr/bin/env python
#
#  export_tests.py:  testing export cases.
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
import tempfile

# Our testing module
import svntest


# (abbreviation)
Skip = svntest.testcase.Skip_deco
SkipUnless = svntest.testcase.SkipUnless_deco
XFail = svntest.testcase.XFail_deco
Issues = svntest.testcase.Issues_deco
Issue = svntest.testcase.Issue_deco
Wimp = svntest.testcase.Wimp_deco
Item = svntest.wc.StateItem


######################################################################
# Tests
#
#   Each test must return on success or raise on failure.


#----------------------------------------------------------------------

def export_empty_directory(sbox):
  "export an empty directory"
  sbox.build(create_wc = False, read_only = True)

  svntest.main.safe_rmtree(sbox.wc_dir)
  export_target = sbox.wc_dir
  empty_dir_url = sbox.repo_url + '/A/C'
  svntest.main.run_svn(None, 'export', empty_dir_url, export_target)
  if not os.path.exists(export_target):
    raise svntest.Failure

def export_greek_tree(sbox):
  "export the greek tree"
  sbox.build(create_wc = False, read_only = True)

  svntest.main.safe_rmtree(sbox.wc_dir)
  export_target = sbox.wc_dir
  expected_output = svntest.main.greek_state.copy()
  expected_output.wc_dir = sbox.wc_dir
  expected_output.desc[''] = Item()
  expected_output.tweak(contents=None, status='A ')

  svntest.actions.run_and_verify_export(sbox.repo_url,
                                        export_target,
                                        expected_output,
                                        svntest.main.greek_state.copy())

def export_nonexistent_url(sbox):
  "attempt to export a nonexistent URL"
  sbox.build(create_wc = False, read_only = True)

  svntest.main.safe_rmtree(sbox.wc_dir)
  export_target = os.path.join(sbox.wc_dir, 'nonexistent')
  nonexistent_url = sbox.repo_url + "/nonexistent"
  svntest.actions.run_and_verify_svn(None, svntest.verify.AnyOutput,
                                     'export', nonexistent_url, export_target)

def export_working_copy(sbox):
  "export working copy"
  sbox.build(read_only = True)

  export_target = sbox.add_wc_path('export')
  expected_output = svntest.wc.State(export_target, {
    'A'                 : Item(status='A '),
    'A/B'               : Item(status='A '),
    'A/B/E'             : Item(status='A '),
    'A/B/E/alpha'       : Item(status='A '),
    'A/B/E/beta'        : Item(status='A '),
    'A/B/F'             : Item(status='A '),
    'A/B/lambda'        : Item(status='A '),
    'A/D'               : Item(status='A '),
    'A/D/G'             : Item(status='A '),
    'A/D/G/rho'         : Item(status='A '),
    'A/D/G/pi'          : Item(status='A '),
    'A/D/G/tau'         : Item(status='A '),
    'A/D/H'             : Item(status='A '),
    'A/D/H/chi'         : Item(status='A '),
    'A/D/H/psi'         : Item(status='A '),
    'A/D/H/omega'       : Item(status='A '),
    'A/D/gamma'         : Item(status='A '),
    'A/mu'              : Item(status='A '),
    'A/C'               : Item(status='A '),
    'iota'              : Item(status='A '),
  })

  svntest.actions.run_and_verify_export(sbox.wc_dir,
                                        export_target,
                                        expected_output,
                                        svntest.main.greek_state.copy())

def export_working_copy_with_mods(sbox):
  "export working copy with mods"
  sbox.build(read_only = True)

  wc_dir = sbox.wc_dir

  # Make a couple of local mods to files
  mu_path = os.path.join(wc_dir, 'A', 'mu')
  rho_path = os.path.join(wc_dir, 'A', 'D', 'G', 'rho')
  kappa_path = os.path.join(wc_dir, 'kappa')
  gamma_path = os.path.join(wc_dir, 'A', 'D', 'gamma')
  E_path = os.path.join(wc_dir, 'A', 'B', 'E')

  svntest.main.file_append(mu_path, 'appended mu text')
  svntest.main.file_append(rho_path, 'new appended text for rho')

  svntest.main.file_append(kappa_path, "This is the file 'kappa'.")
  svntest.main.run_svn(None, 'add', kappa_path)
  svntest.main.run_svn(None, 'rm', E_path, gamma_path)

  expected_disk = svntest.main.greek_state.copy()
  expected_disk.tweak('A/mu',
                      contents=expected_disk.desc['A/mu'].contents
                      + 'appended mu text')
  expected_disk.tweak('A/D/G/rho',
                      contents=expected_disk.desc['A/D/G/rho'].contents
                      + 'new appended text for rho')
  expected_disk.add({'kappa' : Item("This is the file 'kappa'.")})
  expected_disk.remove('A/B/E/alpha', 'A/B/E/beta', 'A/B/E', 'A/D/gamma')

  export_target = sbox.add_wc_path('export')

  expected_output = svntest.wc.State(export_target, {
    'A'                 : Item(status='A '),
    'A/D'               : Item(status='A '),
    'A/D/H'             : Item(status='A '),
    'A/D/H/chi'         : Item(status='A '),
    'A/D/H/omega'       : Item(status='A '),
    'A/D/H/psi'         : Item(status='A '),
    'A/D/G'             : Item(status='A '),
    'A/D/G/rho'         : Item(status='A '),
    'A/D/G/pi'          : Item(status='A '),
    'A/D/G/tau'         : Item(status='A '),
    'A/mu'              : Item(status='A '),
    'A/B'               : Item(status='A '),
    #'A/B/E'             : Item(status='A '), # Used to be reported as added
    'A/B/lambda'        : Item(status='A '),
    'A/B/F'             : Item(status='A '),
    'A/C'               : Item(status='A '),
    'iota'              : Item(status='A '),
    'kappa'             : Item(status='A '),
  })

  svntest.actions.run_and_verify_export(sbox.wc_dir,
                                        export_target,
                                        expected_output,
                                        expected_disk)

def export_over_existing_dir(sbox):
  "export over existing dir"
  sbox.build(read_only = True)

  export_target = sbox.add_wc_path('export')

  # Create the target directory which should cause
  # the export operation to fail.
  os.mkdir(export_target)

  svntest.actions.run_and_verify_svn(None, svntest.verify.AnyOutput,
                                     'export', sbox.wc_dir, export_target)

  # As an extra precaution, make sure export_target doesn't have
  # anything in it.
  if len(os.listdir(export_target)):
    raise svntest.Failure("Unexpected files/directories in " + export_target)

def export_keyword_translation(sbox):
  "export with keyword translation"
  sbox.build()

  wc_dir = sbox.wc_dir

  # Add a keyword to A/mu and set the svn:keywords property
  # appropriately to make sure it's translated during
  # the export operation
  mu_path = os.path.join(wc_dir, 'A', 'mu')
  svntest.main.file_append(mu_path, '$LastChangedRevision$')
  svntest.main.run_svn(None, 'ps', 'svn:keywords',
                       'LastChangedRevision', mu_path)
  svntest.main.run_svn(None, 'ci',
                       '-m', 'Added keyword to mu', mu_path)

  expected_disk = svntest.main.greek_state.copy()
  expected_disk.tweak('A/mu',
                      contents=expected_disk.desc['A/mu'].contents +
                      '$LastChangedRevision: 2 $')

  export_target = sbox.add_wc_path('export')

  expected_output = svntest.main.greek_state.copy()
  expected_output.wc_dir = export_target
  expected_output.desc[''] = Item()
  expected_output.tweak(contents=None, status='A ')

  svntest.actions.run_and_verify_export(sbox.repo_url,
                                        export_target,
                                        expected_output,
                                        expected_disk)

def export_eol_translation(sbox):
  "export with eol translation"
  sbox.build()

  wc_dir = sbox.wc_dir

  # Set svn:eol-style to 'CR' to see if it's applied correctly in the
  # export operation
  mu_path = os.path.join(wc_dir, 'A', 'mu')
  svntest.main.run_svn(None, 'ps', 'svn:eol-style',
                       'CR', mu_path)
  svntest.main.run_svn(None, 'ci',
                       '-m', 'Added eol-style prop to mu', mu_path)

  expected_disk = svntest.main.greek_state.copy()
  new_contents = expected_disk.desc['A/mu'].contents.replace("\n", "\r")
  expected_disk.tweak('A/mu', contents=new_contents)

  export_target = sbox.add_wc_path('export')

  expected_output = svntest.main.greek_state.copy()
  expected_output.wc_dir = export_target
  expected_output.desc[''] = Item()
  expected_output.tweak(contents=None, status='A ')

  svntest.actions.run_and_verify_export2(sbox.repo_url,
                                         export_target,
                                         expected_output,
                                         expected_disk,
                                         keep_eol_style=True)

def export_working_copy_with_keyword_translation(sbox):
  "export working copy with keyword translation"
  sbox.build(read_only = True)

  wc_dir = sbox.wc_dir

  # Add a keyword to A/mu and set the svn:keywords property
  # appropriately to make sure it's translated during
  # the export operation
  mu_path = os.path.join(wc_dir, 'A', 'mu')
  svntest.main.file_append(mu_path, '$LastChangedRevision$')
  svntest.main.run_svn(None, 'ps', 'svn:keywords',
                       'LastChangedRevision', mu_path)

  expected_disk = svntest.main.greek_state.copy()
  expected_disk.tweak('A/mu',
                      contents=expected_disk.desc['A/mu'].contents +
                      '$LastChangedRevision: 1M $')

  export_target = sbox.add_wc_path('export')

  expected_output = svntest.wc.State(export_target, {
    'A'                 : Item(status='A '),
    'A/B'               : Item(status='A '),
    'A/B/E'             : Item(status='A '),
    'A/B/E/alpha'       : Item(status='A '),
    'A/B/E/beta'        : Item(status='A '),
    'A/B/F'             : Item(status='A '),
    'A/B/lambda'        : Item(status='A '),
    'A/D'               : Item(status='A '),
    'A/D/G'             : Item(status='A '),
    'A/D/G/pi'          : Item(status='A '),
    'A/D/G/rho'         : Item(status='A '),
    'A/D/G/tau'         : Item(status='A '),
    'A/D/H'             : Item(status='A '),
    'A/D/H/psi'         : Item(status='A '),
    'A/D/H/chi'         : Item(status='A '),
    'A/D/H/omega'       : Item(status='A '),
    'A/D/gamma'         : Item(status='A '),
    'A/C'               : Item(status='A '),
    'A/mu'              : Item(status='A '),
    'iota'              : Item(status='A '),
  })

  svntest.actions.run_and_verify_export(wc_dir,
                                        export_target,
                                        expected_output,
                                        expected_disk)

def export_working_copy_with_property_mods(sbox):
  "export working copy with property mods"
  sbox.build(read_only = True)

  wc_dir = sbox.wc_dir

  # Make a local property mod to A/mu
  mu_path = os.path.join(wc_dir, 'A', 'mu')
  svntest.main.run_svn(None, 'ps', 'svn:eol-style',
                       'CR', mu_path)

  expected_disk = svntest.main.greek_state.copy()
  new_contents = expected_disk.desc['A/mu'].contents.replace("\n", "\r")
  expected_disk.tweak('A/mu', contents=new_contents)

  export_target = sbox.add_wc_path('export')

  expected_output = svntest.wc.State(export_target, {
    'A'                 : Item(status='A '),
    'A/B'               : Item(status='A '),
    'A/B/E'             : Item(status='A '),
    'A/B/E/alpha'       : Item(status='A '),
    'A/B/E/beta'        : Item(status='A '),
    'A/B/F'             : Item(status='A '),
    'A/B/lambda'        : Item(status='A '),
    'A/D'               : Item(status='A '),
    'A/D/G'             : Item(status='A '),
    'A/D/G/pi'          : Item(status='A '),
    'A/D/G/rho'         : Item(status='A '),
    'A/D/G/tau'         : Item(status='A '),
    'A/D/H'             : Item(status='A '),
    'A/D/H/psi'         : Item(status='A '),
    'A/D/H/chi'         : Item(status='A '),
    'A/D/H/omega'       : Item(status='A '),
    'A/D/gamma'         : Item(status='A '),
    'A/C'               : Item(status='A '),
    'A/mu'              : Item(status='A '),
    'iota'              : Item(status='A '),
  })

  svntest.actions.run_and_verify_export2(wc_dir,
                                         export_target,
                                         expected_output,
                                         expected_disk,
                                         keep_eol_style=True)

@XFail()
@Issue(3798)
def export_working_copy_at_base_revision(sbox):
  "export working copy at base revision"
  sbox.build(read_only = True)

  wc_dir = sbox.wc_dir

  mu_path = os.path.join(wc_dir, 'A', 'mu')
  C_path = os.path.join(wc_dir, 'A', 'C')
  kappa_path = os.path.join(wc_dir, 'kappa')
  K_path = os.path.join(wc_dir, 'K')
  gamma_path = os.path.join(wc_dir, 'A', 'D', 'gamma')
  E_path = os.path.join(wc_dir, 'A', 'B', 'E')
  rho_path = os.path.join(wc_dir, 'A', 'D', 'G', 'rho')
  H_path = os.path.join(wc_dir, 'A', 'D', 'H')
  phi_path = os.path.join(wc_dir, 'A', 'D', 'H', 'phi')
  chi_path = os.path.join(wc_dir, 'A', 'D', 'H', 'chi')

  # Make some local modifications: modify mu and C, add kappa and K, delete
  # gamma and E, and replace rho and H.
  # These modifications should *not* get exported at the base revision.
  svntest.main.file_append(mu_path, 'Appended text')
  svntest.main.run_svn(None, 'propset', 'p', 'v', mu_path, C_path)
  svntest.main.file_append(kappa_path, "This is the file 'kappa'.")
  svntest.main.run_svn(None, 'add', kappa_path)
  svntest.main.run_svn(None, 'mkdir', K_path)
  svntest.main.run_svn(None, 'rm', E_path, gamma_path)
  svntest.main.run_svn(None, 'rm', rho_path)
  svntest.main.file_append(rho_path, "Replacement file 'rho'.")
  svntest.main.run_svn(None, 'add', rho_path)
  svntest.main.run_svn(None, 'rm', H_path)
  svntest.main.run_svn(None, 'mkdir', H_path)
  svntest.main.file_append(phi_path, "This is the file 'phi'.")
  svntest.main.run_svn(None, 'add', phi_path)
  svntest.main.file_append(chi_path, "Replacement file 'chi'.")
  svntest.main.run_svn(None, 'add', chi_path)

  # Note that we don't tweak the expected disk tree at all,
  # since the modifications should not be present.
  expected_disk = svntest.main.greek_state.copy()

  export_target = sbox.add_wc_path('export')

  expected_output = svntest.wc.State(export_target, {
    'A'                 : Item(status='A '),
    'A/C'               : Item(status='A '),
    'A/D'               : Item(status='A '),
    'A/D/gamma'         : Item(status='A '),
    'A/D/G'             : Item(status='A '),
    'A/D/G/pi'          : Item(status='A '),
    'A/D/G/tau'         : Item(status='A '),
    'A/D/G/rho'         : Item(status='A '),
    'A/D/H'             : Item(status='A '),
    'A/D/H/psi'         : Item(status='A '),
    'A/D/H/omega'       : Item(status='A '),
    'A/D/H/chi'         : Item(status='A '),
    'A/B'               : Item(status='A '),
    'A/B/F'             : Item(status='A '),
    'A/B/lambda'        : Item(status='A '),
    'A/B/E'             : Item(status='A '),
    'A/B/E/beta'        : Item(status='A '),
    'A/B/E/alpha'       : Item(status='A '),
    'A/mu'              : Item(status='A '),
    'K'                 : Item(status='A '),
    'iota'              : Item(status='A '),
  })

  svntest.actions.run_and_verify_export(wc_dir,
                                        export_target,
                                        expected_output,
                                        expected_disk,
                                        '-rBASE')

def export_native_eol_option(sbox):
  "export with --native-eol"
  sbox.build()

  wc_dir = sbox.wc_dir

  # Append a '\n' to A/mu and set svn:eol-style to 'native'
  # to see if it's applied correctly in the export operation
  mu_path = os.path.join(wc_dir, 'A', 'mu')
  svntest.main.run_svn(None, 'ps', 'svn:eol-style',
                       'native', mu_path)
  svntest.main.run_svn(None, 'ci',
                       '-m', 'Added eol-style prop to mu', mu_path)

  expected_disk = svntest.main.greek_state.copy()
  new_contents = expected_disk.desc['A/mu'].contents.replace("\n", "\r")
  expected_disk.tweak('A/mu', contents=new_contents)

  export_target = sbox.add_wc_path('export')

  expected_output = svntest.main.greek_state.copy()
  expected_output.wc_dir = export_target
  expected_output.desc[''] = Item()
  expected_output.tweak(contents=None, status='A ')

  svntest.actions.run_and_verify_export2(sbox.repo_url,
                                         export_target,
                                         expected_output,
                                         expected_disk,
                                         True,
                                         '--native-eol','CR')

def export_nonexistent_file(sbox):
  "export nonexistent file"
  sbox.build(read_only = True)

  wc_dir = sbox.wc_dir

  kappa_path = os.path.join(wc_dir, 'kappa')

  export_target = sbox.add_wc_path('export')

  svntest.actions.run_and_verify_svn(None, svntest.verify.AnyOutput,
                                     'export', kappa_path, export_target)

def export_unversioned_file(sbox):
  "export unversioned file"
  sbox.build(read_only = True)

  wc_dir = sbox.wc_dir

  kappa_path = os.path.join(wc_dir, 'kappa')
  svntest.main.file_append(kappa_path, "This is the file 'kappa'.")

  export_target = sbox.add_wc_path('export')

  svntest.actions.run_and_verify_svn(None, svntest.verify.AnyOutput,
                                     'export', kappa_path, export_target)

def export_with_state_deleted(sbox):
  "export with state deleted=true"
  sbox.build()

  wc_dir = sbox.wc_dir

  # state deleted=true caused export to crash
  alpha_path = os.path.join(wc_dir, 'A', 'B', 'E', 'alpha')
  svntest.actions.run_and_verify_svn(None, [], 'rm', alpha_path)
  expected_output = svntest.wc.State(wc_dir, {
    'A/B/E/alpha' : Item(verb='Deleting'),
    })
  expected_status = svntest.actions.get_virginal_state(wc_dir, 1)
  expected_status.remove('A/B/E/alpha')
  svntest.actions.run_and_verify_commit(wc_dir,
                                        expected_output, expected_status)

  export_target = sbox.add_wc_path('export')
  expected_output = svntest.wc.State(export_target, {
    'A'                 : Item(status='A '),
    'A/B'               : Item(status='A '),
    'A/B/E'             : Item(status='A '),
    'A/B/E/beta'        : Item(status='A '),
    'A/B/F'             : Item(status='A '),
    'A/B/lambda'        : Item(status='A '),
    'A/D'               : Item(status='A '),
    'A/D/G'             : Item(status='A '),
    'A/D/G/rho'         : Item(status='A '),
    'A/D/G/tau'         : Item(status='A '),
    'A/D/G/pi'          : Item(status='A '),
    'A/D/H'             : Item(status='A '),
    'A/D/H/chi'         : Item(status='A '),
    'A/D/H/psi'         : Item(status='A '),
    'A/D/H/omega'       : Item(status='A '),
    'A/D/gamma'         : Item(status='A '),
    'A/C'               : Item(status='A '),
    'A/mu'              : Item(status='A '),
    'iota'              : Item(status='A '),
  })
  expected_disk = svntest.main.greek_state.copy()
  expected_disk.remove('A/B/E/alpha')
  svntest.actions.run_and_verify_export(sbox.wc_dir,
                                        export_target,
                                        expected_output,
                                        expected_disk)

def export_creates_intermediate_folders(sbox):
  "export and create some intermediate folders"
  sbox.build(create_wc = False, read_only = True)

  svntest.main.safe_rmtree(sbox.wc_dir)
  export_target = os.path.join(sbox.wc_dir, 'a', 'b', 'c')
  expected_output = svntest.main.greek_state.copy()
  expected_output.wc_dir = export_target
  expected_output.desc[''] = Item()
  expected_output.tweak(contents=None, status='A ')

  svntest.actions.run_and_verify_export(sbox.repo_url,
                                        export_target,
                                        expected_output,
                                        svntest.main.greek_state.copy())

def export_HEADplus1_fails(sbox):
  "export -r {HEAD+1} fails"

  sbox.build(create_wc = False, read_only = True)

  svntest.actions.run_and_verify_svn(None, '.*No such revision.*',
                                     'export', sbox.repo_url, sbox.wc_dir,
                                     '-r', 38956)

def export_url_to_explicit_cwd(sbox):
  "export a single file to '.', via url"
  sbox.build(create_wc = False, read_only = True)

  svntest.main.safe_rmtree(sbox.wc_dir)
  expected_output = svntest.wc.State('', {
      'iota': Item(status='A '),
      })
  expected_disk = svntest.wc.State('', {
      'iota': Item(contents="This is the file 'iota'.\n"),
      })

  os.mkdir(sbox.wc_dir)
  os.chdir(sbox.wc_dir)
  svntest.actions.run_and_verify_export(sbox.repo_url + '/iota',
                                        '.', expected_output,
                                        expected_disk)

def export_file_to_explicit_cwd(sbox):
  "export a single file to '.', via wc"
  sbox.build(create_wc = True, read_only = True)

  iota_path = os.path.abspath(os.path.join(sbox.wc_dir, 'iota'))

  tmpdir = sbox.get_tempname('file-exports')
  expected_output = svntest.wc.State('', {
      'iota': Item(status='A '),
      })
  expected_disk = svntest.wc.State('', {
      'iota': Item(contents="This is the file 'iota'.\n"),
      })

  os.mkdir(tmpdir)
  os.chdir(tmpdir)
  svntest.actions.run_and_verify_export(iota_path,
                                        '.', expected_output,
                                        expected_disk)

@Issue(3799)
def export_file_overwrite_fails(sbox):
  "exporting a file refuses to silently overwrite"
  sbox.build(create_wc = True, read_only = True)

  iota_path = os.path.abspath(os.path.join(sbox.wc_dir, 'iota'))
  iota_url = sbox.repo_url + '/iota'
  not_iota_contents = "This obstructs 'iota'.\n"

  tmpdir = sbox.get_tempname('file-overwrites')
  os.mkdir(tmpdir)

  # Run it for source local
  with open(os.path.join(tmpdir, 'iota'), 'w') as f:
    f.write(not_iota_contents)
  svntest.actions.run_and_verify_svn([], '.*exist.*',
                                     'export', iota_path, tmpdir)

  # Verify it failed
  expected_disk = svntest.wc.State('', {
      'iota': Item(contents=not_iota_contents),
      })
  svntest.actions.verify_disk(tmpdir, expected_disk)

  # Run it for source URL
  with open(os.path.join(tmpdir, 'iota'), 'w') as f:
    f.write(not_iota_contents)
  svntest.actions.run_and_verify_svn([], '.*exist.*',
                                     'export', iota_url, tmpdir)

  # Verify it failed
  expected_disk = svntest.wc.State('', {
      'iota': Item(contents=not_iota_contents),
      })
  svntest.actions.verify_disk(tmpdir, expected_disk)

def export_ignoring_keyword_translation(sbox):
  "export ignoring keyword translation"
  sbox.build()

  wc_dir = sbox.wc_dir

  # Add a keyword to A/mu and set the svn:keywords property
  # appropriately to make sure it's not translated during
  # the export operation
  mu_path = os.path.join(wc_dir, 'A', 'mu')
  svntest.main.file_append(mu_path, '$LastChangedRevision$')
  svntest.main.run_svn(None, 'ps', 'svn:keywords',
                       'LastChangedRevision', mu_path)
  svntest.main.run_svn(None, 'ci',
                       '-m', 'Added keyword to mu', mu_path)

  expected_disk = svntest.main.greek_state.copy()
  expected_disk.tweak('A/mu',
                      contents=expected_disk.desc['A/mu'].contents +
                      '$LastChangedRevision$')

  export_target = sbox.add_wc_path('export')

  expected_output = svntest.main.greek_state.copy()
  expected_output.wc_dir = export_target
  expected_output.desc[''] = Item()
  expected_output.tweak(contents=None, status='A ')

  svntest.actions.run_and_verify_export(sbox.repo_url,
                                        export_target,
                                        expected_output,
                                        expected_disk,
                                        "--ignore-keywords")

def export_working_copy_ignoring_keyword_translation(sbox):
  "export working copy ignoring keyword translation"
  sbox.build(read_only = True)

  wc_dir = sbox.wc_dir

  # Add a keyword to A/mu and set the svn:keywords property
  # appropriately to make sure it's not translated during
  # the export operation
  mu_path = os.path.join(wc_dir, 'A', 'mu')
  svntest.main.file_append(mu_path, '$LastChangedRevision$')
  svntest.main.run_svn(None, 'ps', 'svn:keywords',
                       'LastChangedRevision', mu_path)

  expected_disk = svntest.main.greek_state.copy()
  expected_disk.tweak('A/mu',
                      contents=expected_disk.desc['A/mu'].contents +
                      '$LastChangedRevision$')

  export_target = sbox.add_wc_path('export')

  expected_output = svntest.wc.State(export_target, {
    'A'                 : Item(status='A '),
    'A/D'               : Item(status='A '),
    'A/D/G'             : Item(status='A '),
    'A/D/G/rho'         : Item(status='A '),
    'A/D/G/pi'          : Item(status='A '),
    'A/D/G/tau'         : Item(status='A '),
    'A/D/H'             : Item(status='A '),
    'A/D/H/psi'         : Item(status='A '),
    'A/D/H/omega'       : Item(status='A '),
    'A/D/H/chi'         : Item(status='A '),
    'A/D/gamma'         : Item(status='A '),
    'A/B'               : Item(status='A '),
    'A/B/E'             : Item(status='A '),
    'A/B/E/alpha'       : Item(status='A '),
    'A/B/E/beta'        : Item(status='A '),
    'A/B/F'             : Item(status='A '),
    'A/B/lambda'        : Item(status='A '),
    'A/C'               : Item(status='A '),
    'A/mu'              : Item(status='A '),
    'iota'              : Item(status='A '),
  })

  svntest.actions.run_and_verify_export(wc_dir,
                                        export_target,
                                        expected_output,
                                        expected_disk,
                                        "--ignore-keywords")

# This is test for issue #3683 - 'Escape unsafe charaters in a URL during
# export'
@Issue(3683)
def export_with_url_unsafe_characters(sbox):
  "export file with URL unsafe characters"

  ## See https://issues.apache.org/jira/browse/SVN-3683 ##

  sbox.build()
  wc_dir = sbox.wc_dir

  # Define the paths
  url_unsafe_path = os.path.join(wc_dir, 'A', 'test- @#$&.txt')
  url_unsafe_path_url = sbox.repo_url + '/A/test- @#$&.txt@'
  export_target = os.path.join(wc_dir, 'test- @#$&.txt')

  # Create the file with special name and commit it.
  svntest.main.file_write(url_unsafe_path, 'This is URL unsafe path file.')
  svntest.main.run_svn(None, 'add', url_unsafe_path + '@')
  svntest.actions.run_and_verify_svn(None, [], 'ci', '-m', 'log msg',
                                     '--quiet', wc_dir)

  # Export the file and verify it.
  svntest.actions.run_and_verify_svn(None, [], 'export',
                                     url_unsafe_path_url, export_target + '@')

  if not os.path.exists(export_target):
    raise svntest.Failure("export did not fetch file with URL unsafe path")

@Issue(3800)
def export_working_copy_with_depths(sbox):
  "export working copy with different depths"
  sbox.build(read_only = True)

  expected_disk = svntest.wc.State('', {
      'A': Item(),
      'iota': Item(contents="This is the file 'iota'.\n"),
      })
  export_target = sbox.add_wc_path('immediates')
  expected_output = svntest.wc.State(export_target, {
    'iota'              : Item(status='A '),
    'A'                 : Item(status='A '),
  })
  svntest.actions.run_and_verify_export(sbox.wc_dir,
                                        export_target,
                                        expected_output,
                                        expected_disk,
                                        '--depth=immediates')

  expected_disk.remove('A')
  export_target = sbox.add_wc_path('files')
  expected_output = svntest.wc.State(export_target, {
    'iota'              : Item(status='A '),
  })
  svntest.actions.run_and_verify_export(sbox.wc_dir,
                                        export_target,
                                        expected_output,
                                        expected_disk,
                                        '--depth=files')

  expected_disk.remove('iota')
  expected_output = svntest.wc.State(export_target, {
  })
  export_target = sbox.add_wc_path('empty')
  svntest.actions.run_and_verify_export(sbox.wc_dir,
                                        export_target,
                                        expected_output,
                                        expected_disk,
                                        '--depth=empty')

def export_externals_with_native_eol(sbox):
  "export externals with eol translation"
  sbox.build()

  wc_dir = sbox.wc_dir

  # Set svn:eol-style to 'native' to see if it's applied correctly to
  # externals in the export operation
  alpha_path = os.path.join(wc_dir, 'A', 'B', 'E', 'alpha')
  svntest.main.run_svn(None, 'ps', 'svn:eol-style', 'native', alpha_path)
  svntest.main.run_svn(None, 'ci',
                       '-m', 'Added eol-style prop to alpha', alpha_path)

  # Set 'svn:externals' property in 'A/C' to 'A/B/E/alpha'(file external),
  # 'A/B/E'(directory external) & commit the property
  C_path = os.path.join(wc_dir, 'A', 'C')
  externals_prop = """^/A/B/E/alpha exfile_alpha
  ^/A/B/E exdir_E"""

  tmp_f = sbox.get_tempname('props')
  svntest.main.file_append(tmp_f, externals_prop)
  svntest.main.run_svn(None, 'ps', '-F', tmp_f, 'svn:externals', C_path)
  svntest.main.run_svn(None,'ci', '-m', 'log msg', '--quiet', C_path)


  # Update the working copy to receive all changes(file external and
  # directroy external changes) from repository
  svntest.main.run_svn(None, 'up', wc_dir)

  # After export, expected_disk will have all those present in standard
  # greek tree and new externals we added above.
  # Update the expected disk tree to include all those externals.
  expected_disk = svntest.main.greek_state.copy()
  expected_disk.add({
      'A/C/exfile_alpha'  : Item("This is the file 'alpha'.\n"),
      'A/C/exdir_E'       : Item(),
      'A/C/exdir_E/alpha' : Item("This is the file 'alpha'.\n"),
      'A/C/exdir_E/beta'  : Item("This is the file 'beta'.\n")
      })

  # We are exporting with '--native-eol CR' option.
  # So change the contents of files under *expected_disk* tree
  # which have svn:eol-style property set to 'native' to verify
  # with the exported tree.
  # Here A/B/E/alpha and its external manifestations A/C/exfile_alpha
  # and A/C/exdir_E/alpha needs a tweak.
  new_contents = expected_disk.desc['A/C/exfile_alpha'].contents.replace("\n",
                                                                         "\r")
  expected_disk.tweak('A/C/exfile_alpha', 'A/B/E/alpha','A/C/exdir_E/alpha',
                      contents=new_contents)

  expected_output = svntest.main.greek_state.copy()
  expected_output.add({
      'A/C/exfile_alpha'  : Item("This is the file 'alpha'.\r"),
      'A/C/exdir_E'       : Item(),
      'A/C/exdir_E/alpha' : Item("This is the file 'alpha'.\r"),
      'A/C/exdir_E/beta'  : Item("This is the file 'beta'.\n")
      })

  # Export the repository with '--native-eol CR' option
  export_target = sbox.add_wc_path('export')
  expected_output.wc_dir = export_target
  expected_output.desc[''] = Item()
  expected_output.tweak(contents=None, status='A ')
  svntest.actions.run_and_verify_export2(sbox.repo_url,
                                         export_target,
                                         expected_output,
                                         expected_disk,
                                         True,
                                         '--native-eol', 'CR')

@Issue(3727)
def export_to_current_dir(sbox):
  "export to current dir"
  # Issue 3727: Forced export in current dir creates unexpected subdir.
  sbox.build(create_wc = False, read_only = True)

  svntest.main.safe_rmtree(sbox.wc_dir)
  os.mkdir(sbox.wc_dir)

  orig_dir = os.getcwd()
  os.chdir(sbox.wc_dir)

  export_url = sbox.repo_url + '/A/B/E'
  export_target = '.'
  expected_output = svntest.wc.State('', {
    '.'         : Item(status='A '),
    'alpha'     : Item(status='A '),
    'beta'      : Item(status='A '),
    })
  expected_disk = svntest.wc.State('', {
    'alpha'     : Item("This is the file 'alpha'.\n"),
    'beta'      : Item("This is the file 'beta'.\n"),
    })
  svntest.actions.run_and_verify_export(export_url,
                                        export_target,
                                        expected_output,
                                        expected_disk,
                                        '--force')

  os.chdir(orig_dir)

def export_file_overwrite_with_force(sbox):
  "exporting a file with force option"
  sbox.build(create_wc = True, read_only = True)

  iota_path = os.path.abspath(os.path.join(sbox.wc_dir, 'iota'))
  iota_url = sbox.repo_url + '/iota'
  not_iota_contents = "This obstructs 'iota'.\n"
  iota_contents = "This is the file 'iota'.\n"

  tmpdir = sbox.get_tempname('file-overwrites')
  os.mkdir(tmpdir)

  expected_disk = svntest.wc.State('', {
      'iota': Item(contents=iota_contents),
      })

  # Run it for WC export
  with open(os.path.join(tmpdir, 'iota'), 'w') as f:
    f.write(not_iota_contents)
  svntest.actions.run_and_verify_svn(svntest.verify.AnyOutput,
                                     [], 'export', '--force',
                                     iota_path, tmpdir)
  svntest.actions.verify_disk(tmpdir, expected_disk)

  # Run it for URL export
  with open(os.path.join(tmpdir, 'iota'), 'w') as f:
    f.write(not_iota_contents)
  svntest.actions.run_and_verify_svn(svntest.verify.AnyOutput,
                                     [], 'export', '--force',
                                     iota_url, tmpdir)
  svntest.actions.verify_disk(tmpdir, expected_disk)

def export_custom_keywords(sbox):
  """export with custom keywords"""

  sbox.build()
  wc_dir = sbox.wc_dir

  # 248=SVN_KEYWORD_MAX_LEN-7 where 7 is '$', 'Q', 'q', ':', ' ', ' ', '$'
  alpha_content = ('[$Qq: %s $ $Pp: %s $]\n'
                   % (sbox.repo_url[:248],
                      (sbox.repo_url + '/A/B/E/alpha')[:248]))

  sbox.simple_append('A/B/E/alpha', '[$Qq$ $Pp$]\n', truncate=True)
  sbox.simple_propset('svn:keywords', 'Qq=%R Pp=%u', 'A/B/E/alpha')
  sbox.simple_commit()
  expected_disk = svntest.main.greek_state.copy()
  expected_disk.tweak('A/B/E/alpha', contents=alpha_content)
  svntest.actions.verify_disk(sbox.wc_dir, expected_disk)

  # Export a tree
  export_target = sbox.add_wc_path('export')
  expected_output = svntest.wc.State(export_target, {
    ''             : Item(status='A '),
    'alpha'       : Item(status='A '),
    'beta'        : Item(status='A '),
  })
  expected_disk = svntest.wc.State('', {
      'alpha': Item(contents=alpha_content),
      'beta' : Item(contents="This is the file 'beta'.\n"),
      })
  svntest.actions.run_and_verify_export(sbox.repo_url + '/A/B/E',
                                        export_target,
                                        expected_output,
                                        expected_disk)

  # Export a file
  export_file = os.path.join(export_target, 'alpha')
  os.remove(export_file)
  expected_output = ['A    %s\n' % export_file, 'Export complete.\n']
  svntest.actions.run_and_verify_svn(expected_output, [],
                                     'export', '--force',
                                     sbox.repo_url + '/A/B/E/alpha',
                                     export_target)

  if open(export_file).read() != ''.join(alpha_content):
    raise svntest.Failure("wrong keyword expansion")

@Issue(4427)
def export_file_external(sbox):
  "export file external from WC and URL"
  sbox.build()

  wc_dir = sbox.wc_dir

  # Set 'svn:externals' property in 'A/C' to 'A/B/E/alpha'(file external),
  C_path = os.path.join(wc_dir, 'A', 'C')
  externals_prop = "^/A/B/E/alpha exfile_alpha"

  tmp_f = sbox.get_tempname('prop')
  svntest.main.file_append(tmp_f, externals_prop)
  svntest.main.run_svn(None, 'ps', '-F', tmp_f, 'svn:externals', C_path)
  svntest.main.run_svn(None,'ci', '-m', 'log msg', '--quiet', C_path)

  # Update the working copy to receive file external
  svntest.main.run_svn(None, 'up', wc_dir)

  # Update the expected disk tree to include the external.
  expected_disk = svntest.main.greek_state.copy()
  expected_disk.add({
      'A/C/exfile_alpha'  : Item("This is the file 'alpha'.\n"),
      })

  # Export from URL
  export_target = sbox.add_wc_path('export_url')
  expected_output = svntest.main.greek_state.copy()
  expected_output.add({
      'A/C/exfile_alpha'  : Item("This is the file 'alpha'.\r"),
      })
  expected_output.wc_dir = export_target
  expected_output.desc[''] = Item()
  expected_output.tweak(contents=None, status='A ')
  svntest.actions.run_and_verify_export(sbox.repo_url,
                                        export_target,
                                        expected_output,
                                        expected_disk)

  # Export from WC
  export_target = sbox.add_wc_path('export_wc')
  expected_output = svntest.main.greek_state.copy()
  expected_output.add({
      'A/C/exfile_alpha'  : Item("This is the file 'alpha'.\r"),
      })
  expected_output.wc_dir = export_target
  expected_output.desc['A'] = Item()
  expected_output.tweak(contents=None, status='A ')
  svntest.actions.run_and_verify_export(wc_dir,
                                        export_target,
                                        expected_output,
                                        expected_disk)

@Issue(4427)
def export_file_externals2(sbox):
  "exporting file externals"

  sbox.build()
  sbox.simple_mkdir('DIR', 'DIR2')

  sbox.simple_propset('svn:externals', '^/iota file', 'DIR')
  sbox.simple_propset('svn:externals', '^/DIR TheDir', 'DIR2')
  sbox.simple_commit()
  sbox.simple_update()

  tmp = sbox.add_wc_path('tmp')
  os.mkdir(tmp)

  expected_output = svntest.wc.State(tmp, {
    'file'          : Item(status='A '),
  })
  expected_disk = svntest.wc.State('', {
    'file': Item(contents="This is the file 'iota'.\n")
  })
  # Fails in 1.8.8 and r1575909.
  # Direct export of file external was just skipped
  svntest.actions.run_and_verify_export(sbox.ospath('DIR/file'),
                                        tmp,
                                        expected_output,
                                        expected_disk)

  expected_output = svntest.wc.State(tmp, {
    'DIR/file'           : Item(status='A '),
  })
  expected_disk = svntest.wc.State('', {
    'file': Item(contents="This is the file 'iota'.\n")
  })
  # Fails in 1.8.8 (doesn't export file), passes in r1575909
  svntest.actions.run_and_verify_export(sbox.ospath('DIR'),
                                        os.path.join(tmp, 'DIR'),
                                        expected_output,
                                        expected_disk)

  expected_output = svntest.wc.State(tmp, {
    'DIR2/TheDir/file' : Item(status='A '),
  })
  expected_disk = svntest.wc.State('', {
    'TheDir'      : Item(),
    'TheDir/file' : Item(contents="This is the file 'iota'.\n")
  })
  # Fails in 1.8.8 (doesn't export anything),
  # Fails in r1575909 (exports file twice; once as file; once as external)
  svntest.actions.run_and_verify_export(sbox.ospath('DIR2'),
                                        os.path.join(tmp, 'DIR2'),
                                        expected_output,
                                        expected_disk)

def export_revision_with_root_relative_external(sbox):
  "export a revision with root-relative external"
  sbox.build()

  wc_dir = sbox.wc_dir

  # Set 'svn:externals' property in 'A/C' to 'A/B/E/alpha'(file external),
  C_path = os.path.join(wc_dir, 'A', 'C')
  externals_prop = "^/A/B/E/alpha exfile_alpha"

  tmp_f = sbox.get_tempname('prop')
  svntest.main.file_append(tmp_f, externals_prop)
  svntest.main.run_svn(None, 'ps', '-F', tmp_f, 'svn:externals', C_path)
  svntest.main.run_svn(None,'ci', '-m', 'log msg', '--quiet', C_path)

  # Update the working copy to receive file external
  svntest.main.run_svn(None, 'up', wc_dir)

  # Update the expected disk tree to include the external.
  expected_disk = svntest.main.greek_state.copy()
  expected_disk.add({
      'A/C/exfile_alpha'  : Item("This is the file 'alpha'.\n"),
      })

  # Update the expected output to include the external.
  expected_output = svntest.main.greek_state.copy()
  expected_output.add({
      'A/C/exfile_alpha'  : Item("This is the file 'alpha'.\r"),
      })
  expected_output.desc[''] = Item()
  expected_output.tweak(contents=None, status='A ')

  # Export revision 2 from URL
  export_target = sbox.add_wc_path('export_url')
  expected_output.wc_dir = export_target
  svntest.actions.run_and_verify_export(sbox.repo_url,
                                        export_target,
                                        expected_output,
                                        expected_disk,
                                        '-r', 2)

  # Export revision 2 from WC
  export_target = sbox.add_wc_path('export_wc')
  expected_output.wc_dir = export_target
  svntest.actions.run_and_verify_export(sbox.wc_dir,
                                        export_target,
                                        expected_output,
                                        expected_disk,
                                        '-r', 2)

def export_keyword_translation_inconsistent_eol(sbox):
  "export keyword translation with inconsistent EOLs"
  sbox.build(empty=True)
  sbox.simple_mkdir('dir')
  # Create a file with keywords and inconsistent EOLs, don't set svn:eol-style.
  sbox.simple_add_text('$LastChangedRevision$\n\r\n', 'dir/file')
  sbox.simple_propset('svn:keywords', 'LastChangedRevision', 'dir/file')
  sbox.simple_commit()

  export_target = sbox.add_wc_path('export')

  expected_disk = svntest.wc.State('', {
    'dir'      : Item(),
    'dir/file' : Item("$LastChangedRevision: 1 $\n\r\n"),
  })

  expected_output = svntest.wc.State(export_target, {
    ''         : Item(status='A '),
    'dir'      : Item(status='A '),
    'dir/file' : Item(status='A ')
  })

  # We should be able to export without any unexpected errors.
  svntest.actions.run_and_verify_export2(sbox.repo_url,
                                         export_target,
                                         expected_output,
                                         expected_disk,
                                         keep_eol_style=True)

def export_working_copy_eol_translation(sbox):
  "export working copy with EOL translation"
  sbox.build(empty=True)
  sbox.simple_mkdir('dir')
  sbox.simple_add_text('test\n', 'dir/file')
  sbox.simple_propset('svn:eol-style', 'CRLF', 'dir/file')
  sbox.simple_commit()

  export_target = sbox.add_wc_path('export')

  expected_disk = svntest.wc.State('', {
    'dir'      : Item(),
    'dir/file' : Item("test\r\n"),
  })

  expected_output = svntest.wc.State(export_target, {
    'dir'      : Item(status='A '),
    'dir/file' : Item(status='A ')
  })

  svntest.actions.run_and_verify_export2(sbox.wc_dir,
                                         export_target,
                                         expected_output,
                                         expected_disk,
                                         keep_eol_style=True)

def export_working_copy_inconsistent_eol(sbox):
  "export working copy with inconsistent EOLs"
  sbox.build(empty=True)
  sbox.simple_mkdir('dir')
  sbox.simple_add_text('test\n', 'dir/file')
  sbox.simple_propset('svn:eol-style', 'CRLF', 'dir/file')
  sbox.simple_commit()

  # Edit the file so that it would have inconsistent EOLs.
  sbox.simple_append('dir/file', 'test\n\r\n', truncate=True)

  # Attempt to export the working copy, expect an error.
  export_target = sbox.add_wc_path('export')
  svntest.actions.run_and_verify_svn(
    None,
    "svn: E135000: Inconsistent line ending style\n",
    'export',
    sbox.wc_dir,
    export_target)


########################################################################
# Run the tests


# list all tests here, starting with None:
test_list = [ None,
              export_empty_directory,
              export_greek_tree,
              export_nonexistent_url,
              export_working_copy,
              export_working_copy_with_mods,
              export_over_existing_dir,
              export_keyword_translation,
              export_eol_translation,
              export_working_copy_with_keyword_translation,
              export_working_copy_with_property_mods,
              export_working_copy_at_base_revision,
              export_native_eol_option,
              export_nonexistent_file,
              export_unversioned_file,
              export_with_state_deleted,
              export_creates_intermediate_folders,
              export_HEADplus1_fails,
              export_url_to_explicit_cwd,
              export_file_to_explicit_cwd,
              export_file_overwrite_fails,
              export_ignoring_keyword_translation,
              export_working_copy_ignoring_keyword_translation,
              export_with_url_unsafe_characters,
              export_working_copy_with_depths,
              export_externals_with_native_eol,
              export_to_current_dir,
              export_file_overwrite_with_force,
              export_custom_keywords,
              export_file_external,
              export_file_externals2,
              export_revision_with_root_relative_external,
              export_keyword_translation_inconsistent_eol,
              export_working_copy_eol_translation,
              export_working_copy_inconsistent_eol,
             ]

if __name__ == '__main__':
  svntest.main.run_tests(test_list)
  # NOTREACHED


### End of file.
