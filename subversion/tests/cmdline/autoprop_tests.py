#!/usr/bin/env python
#
#  autoprop_tests.py:  testing automatic properties
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
import os, logging, stat

logger = logging.getLogger()

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

from svntest.main import SVN_PROP_INHERITABLE_AUTOPROPS

# Helper function
def check_proplist(path, exp_out):
  """Verify that property list on PATH has a value of EXP_OUT"""

  props = svntest.tree.get_props([path]).get(path, {})
  if props != exp_out:
    logger.warn("Expected properties: %s", exp_out)
    logger.warn("Actual properties:   %s", props)
    raise svntest.Failure


######################################################################
# Tests

#----------------------------------------------------------------------

def create_config(sbox, enable_flag):
  "create config directories and files"

  # contents of the file 'config'
  config_contents = '''\
[auth]
password-stores =

[miscellany]
enable-auto-props = %s

[auto-props]
*.c = cfile=yes
*.jpg = jpgfile=ja
fubar* = tarfile=si
foobar.lha = lhafile=da;lzhfile=niet
spacetest = abc = def ; ghi = ; = j
escapetest = myval=;;;;val;myprop=p
quotetest = svn:keywords="Author Date Id Rev URL";
* = auto=oui
''' % (enable_flag and 'yes' or 'no')

  return sbox.create_config_dir(config_contents)

#----------------------------------------------------------------------

def autoprops_test(sbox, cmd, cfgenable, clienable, subdir):
  """configurable autoprops test.

     CMD is the subcommand to test: 'import' or 'add'
     if CFGENABLE is true, enable autoprops in the config file, else disable
     if CLIENABLE == 1: --auto-props is added to the command line
                     0: nothing is added
                    -1: --no-auto-props is added to command line
     if string SUBDIR is not empty files are created in that subdir and the
       directory is added/imported"""

  # Bootstrap
  sbox.build()

  # some directories
  wc_dir = sbox.wc_dir
  tmp_dir = os.path.abspath(sbox.add_wc_path('autoprops'))
  os.makedirs(tmp_dir)
  repos_url = sbox.repo_url

  config_dir = create_config(sbox, cfgenable)

  # initialize parameters
  if cmd == 'import':
    parameters = ['import', '-m', 'bla']
    files_dir = tmp_dir
  else:
    parameters = ['add']
    files_dir = wc_dir

  parameters = parameters + ['--config-dir', config_dir]

  # add comandline flags
  if clienable == 1:
    parameters = parameters + ['--auto-props']
    enable_flag = 1
  elif clienable == -1:
    parameters = parameters + ['--no-auto-props']
    enable_flag = 0
  else:
    enable_flag = cfgenable

  # setup subdirectory if needed
  if len(subdir) > 0:
    files_dir = os.path.join(files_dir, subdir)
    files_wc_dir = os.path.join(wc_dir, subdir)
    os.makedirs(files_dir)
  else:
    files_wc_dir = wc_dir

  # create test files
  filenames = ['foo.h',
               'foo.c',
               'foo.jpg',
               'fubar.tar',
               'foobar.lha',
               'spacetest',
               'escapetest',
               'quotetest']
  for filename in filenames:
    svntest.main.file_write(os.path.join(files_dir, filename),
                            'foo\nbar\nbaz\n')

  if len(subdir) == 0:
    # add/import the files
    for filename in filenames:
      path = os.path.join(files_dir, filename)
      if cmd == 'import':
        tmp_params = parameters + [path, repos_url + '/' + filename]
      else:
        tmp_params = parameters + [path]
      svntest.main.run_svn(None, *tmp_params)
  else:
    # add/import subdirectory
    if cmd == 'import':
      parameters = parameters + [files_dir, repos_url]
    else:
      parameters = parameters + [files_wc_dir]
    svntest.main.run_svn(None, *parameters)

  # do an svn co if needed
  if cmd == 'import':
    svntest.main.run_svn(None, 'checkout', repos_url, files_wc_dir,
                        '--config-dir', config_dir)

  # check the properties
  if enable_flag:
    filename = os.path.join(files_wc_dir, 'foo.h')
    check_proplist(filename, {'auto':'oui'})
    filename = os.path.join(files_wc_dir, 'foo.c')
    check_proplist(filename, {'auto':'oui', 'cfile':'yes'})
    filename = os.path.join(files_wc_dir, 'foo.jpg')
    check_proplist(filename, {'auto':'oui', 'jpgfile':'ja'})
    filename = os.path.join(files_wc_dir, 'fubar.tar')
    check_proplist(filename, {'auto':'oui', 'tarfile':'si'})
    filename = os.path.join(files_wc_dir, 'foobar.lha')
    check_proplist(filename, {'auto':'oui', 'lhafile':'da', 'lzhfile':'niet'})
    filename = os.path.join(files_wc_dir, 'spacetest')
    check_proplist(filename, {'auto':'oui', 'abc':'def', 'ghi':''})
    filename = os.path.join(files_wc_dir, 'escapetest')
    check_proplist(filename, {'auto':'oui', 'myval':';;val', 'myprop':'p'})
    filename = os.path.join(files_wc_dir, 'quotetest')
    check_proplist(filename, {'auto':'oui',
                              'svn:keywords': 'Author Date Id Rev URL'})
  else:
    for filename in filenames:
      check_proplist(os.path.join(files_wc_dir, filename), {})


#----------------------------------------------------------------------

def autoprops_add_no_none(sbox):
  "add: config=no,  commandline=none"

  autoprops_test(sbox, 'add', 0, 0, '')

#----------------------------------------------------------------------

def autoprops_add_yes_none(sbox):
  "add: config=yes, commandline=none"

  autoprops_test(sbox, 'add', 1, 0, '')

#----------------------------------------------------------------------

def autoprops_add_no_yes(sbox):
  "add: config=no,  commandline=yes"

  autoprops_test(sbox, 'add', 0, 1, '')

#----------------------------------------------------------------------

def autoprops_add_yes_yes(sbox):
  "add: config=yes, commandline=yes"

  autoprops_test(sbox, 'add', 1, 1, '')

#----------------------------------------------------------------------

def autoprops_add_no_no(sbox):
  "add: config=no,  commandline=no"

  autoprops_test(sbox, 'add', 0, -1, '')

#----------------------------------------------------------------------

def autoprops_add_yes_no(sbox):
  "add: config=yes, commandline=no"

  autoprops_test(sbox, 'add', 1, -1, '')

#----------------------------------------------------------------------

def autoprops_imp_no_none(sbox):
  "import: config=no,  commandline=none"

  autoprops_test(sbox, 'import', 0, 0, '')

#----------------------------------------------------------------------

def autoprops_imp_yes_none(sbox):
  "import: config=yes, commandline=none"

  autoprops_test(sbox, 'import', 1, 0, '')

#----------------------------------------------------------------------

def autoprops_imp_no_yes(sbox):
  "import: config=no,  commandline=yes"

  autoprops_test(sbox, 'import', 0, 1, '')

#----------------------------------------------------------------------

def autoprops_imp_yes_yes(sbox):
  "import: config=yes, commandline=yes"

  autoprops_test(sbox, 'import', 1, 1, '')

#----------------------------------------------------------------------

def autoprops_imp_no_no(sbox):
  "import: config=no,  commandline=no"

  autoprops_test(sbox, 'import', 0, -1, '')

#----------------------------------------------------------------------

def autoprops_imp_yes_no(sbox):
  "import: config=yes, commandline=no"

  autoprops_test(sbox, 'import', 1, -1, '')

#----------------------------------------------------------------------

def autoprops_add_dir(sbox):
  "add directory"

  autoprops_test(sbox, 'add', 1, 0, 'autodir')

#----------------------------------------------------------------------

def autoprops_imp_dir(sbox):
  "import directory"

  autoprops_test(sbox, 'import', 1, 0, 'autodir')

#----------------------------------------------------------------------

# Issue #2713: adding a file with an svn:eol-style property, svn should abort
# if the file has mixed EOL style. Previously, svn aborted but had added the
# file anyway.
@Issue(2713)
def fail_add_mixed_eol_style(sbox):
  "fail to add a file with mixed EOL style"

  from svntest.actions import run_and_verify_svn, run_and_verify_unquiet_status

  # Bootstrap
  sbox.build()

  filename = 'mixed-eol.txt'
  filepath = os.path.join(sbox.wc_dir, filename)
  parameters = ['--auto-props',
                '--config-option=config:auto-props:' + filename
                + '=svn:eol-style=native']

  svntest.main.file_write(filepath, 'foo\nbar\r\nbaz\r')

  expected_stderr = "svn: E200009: File '.*" + filename + \
                    "' has inconsistent newlines" + \
                    "|" + "svn: E135000: Inconsistent line ending style\n"
  run_and_verify_svn([], expected_stderr,
                     'add', filepath, *parameters)

  expected_status = svntest.wc.State(sbox.wc_dir,
    {filename : Item(status='? ')})
  run_and_verify_unquiet_status(filepath, expected_status)

#----------------------------------------------------------------------

def create_inherited_autoprops_config(sbox, enable_flag):
  "create config stuffs for inherited autoprops tests"

  # contents of the file 'config'
  config_contents = '''\
[auth]
password-stores =

[miscellany]
enable-auto-props = %s

[auto-props]
*.c = svn:keywords=Author Date Id Rev URL;svn:eol-style=native;
''' % (enable_flag and 'yes' or 'no')

  return sbox.create_config_dir(config_contents)

#----------------------------------------------------------------------
def check_inheritable_autoprops(sbox, auto_props_cfg_enabled,
                                inheritable_auto_props_enabled):
  """Check that the autoprops added or imported by inheritable_autoprops_test
     are as expected based on whether auto props are active or
     not, as indicated by AUTO_PROPS_CFG_ENABLED and
     INHERITABLE_AUTO_PROPS_ENABLED."""

  foo_path = sbox.ospath('foo.c')
  bar_path = sbox.ospath('B/bar.c')
  baf_path = sbox.ospath('C/baf.c')
  qux_path = sbox.ospath('D/qux.c')
  rip_path = sbox.ospath('D/rip.bat')
  snk_path = sbox.ospath('D/H/snk.py')
  sir_path = sbox.ospath('D/H/sir.c')

  if auto_props_cfg_enabled:
    check_proplist(foo_path, {'svn:eol-style':'CRLF',
                              'svn:keywords':'Author Date Id Rev URL'})
    check_proplist(bar_path, {'svn:eol-style':'CR',
                              'svn:keywords':'Date'})
    check_proplist(baf_path, {'svn:eol-style':'LF',
                              'svn:keywords':'Rev'})
    check_proplist(qux_path, {'svn:eol-style':'CRLF',
                              'svn:keywords':'Author Date Id Rev URL'})
    check_proplist(rip_path, {'svn:executable':'*'})
    check_proplist(snk_path, {'svn:mime-type':'text/x-python'})
    check_proplist(sir_path, {'svn:eol-style':'CRLF',
                              'svn:keywords':'Author Date Id Rev URL'})
  elif inheritable_auto_props_enabled: # Config auto-props disabled,
                                          # but not svn:auto-props.
    check_proplist(foo_path, {'svn:eol-style':'CRLF'})
    check_proplist(bar_path, {'svn:eol-style':'CR',
                              'svn:keywords':'Date'})
    check_proplist(baf_path, {'svn:eol-style':'LF',
                              'svn:keywords':'Rev'})
    check_proplist(qux_path, {'svn:eol-style':'CRLF'})
    check_proplist(rip_path, {'svn:executable':'*'})
    check_proplist(snk_path, {'svn:mime-type':'text/x-python'})
    check_proplist(sir_path, {'svn:eol-style':'CRLF'})
  else: # No autoprops of any kind.
    check_proplist(foo_path, {})
    check_proplist(bar_path, {})
    check_proplist(baf_path, {})
    check_proplist(qux_path, {})
    check_proplist(rip_path, {})
    check_proplist(snk_path, {})
    check_proplist(sir_path, {})

#----------------------------------------------------------------------
def inheritable_autoprops_test(sbox, cmd, cfgenable, clienable, subdir,
                               do_import_or_add=True):
  """configurable autoprops and svn:auto-props test.

     CMD is the subcommand to test: 'import' or 'add'
     if CFGENABLE is true, enable autoprops in the config file, else disable
     if CLIENABLE == 1: --auto-props is added to the command line
                     0: nothing is added
                    -1: --no-auto-props is added to command line
     if string SUBDIR is not empty files are created in that subdir and the
       directory is added/imported
     if DO_IMPORT_OR_ADD is false, setup the test, but don't perform
       the actual import or add.

     Return the directory where the config dir (if any) is located."""

  # Bootstrap
  sbox.build()

  # some directories
  wc_dir = sbox.wc_dir
  tmp_dir = os.path.abspath(sbox.add_wc_path('iautoprops'))
  os.makedirs(tmp_dir)
  repos_url = sbox.repo_url

  config_dir = create_inherited_autoprops_config(sbox, cfgenable)

  # initialize parameters
  if cmd == 'import':
    parameters = ['import', '-m', 'importing']
    files_dir = tmp_dir
  else:
    parameters = ['add']
    files_dir = wc_dir

  parameters = parameters + ['--config-dir', config_dir]

  # add comandline flags
  inheritable_auto_props_enabled = 1
  if clienable == 1:
    parameters = parameters + ['--auto-props']
    auto_props_cfg_enabled = 1
  elif clienable == -1:
    parameters = parameters + ['--no-auto-props']
    auto_props_cfg_enabled = 0
    inheritable_auto_props_enabled = 0
  else:
    auto_props_cfg_enabled = cfgenable

  # setup subdirectory if needed
  if len(subdir) > 0:
    files_dir = os.path.join(files_dir, subdir)
    files_wc_dir = os.path.join(wc_dir, subdir)
    os.makedirs(files_dir)
  else:
    files_wc_dir = wc_dir

  # Set differing svn:auto-props properties on various
  # directories.
  sbox.simple_propset(SVN_PROP_INHERITABLE_AUTOPROPS,
                      '*.c = svn:eol-style=CRLF\n'
                      '*.bat = svn:executable',
                      '.')
  sbox.simple_propset(SVN_PROP_INHERITABLE_AUTOPROPS,
                      '*.c = svn:eol-style=CR;svn:keywords=Date',
                      'A/B')
  sbox.simple_propset(SVN_PROP_INHERITABLE_AUTOPROPS,
                      '*.c = svn:eol-style=LF;svn:keywords=Rev',
                      'A/C')
  sbox.simple_propset(SVN_PROP_INHERITABLE_AUTOPROPS,
                      '*.py = svn:mime-type=text/x-python',
                      'A/D')
  svntest.actions.run_and_verify_svn(None, [], 'ci', '-m',
                                     'Add some ' + SVN_PROP_INHERITABLE_AUTOPROPS +
                                     ' properties', wc_dir)

  # Switch the root of the WC to ^/A.
  svntest.main.run_svn(None, 'switch', '--ignore-ancestry',
                       sbox.repo_url + '/A', wc_dir)

  # Array of file names to add or import, their WC locations (relative to the
  # WC root) if being added, and their repository locations if being imported.
  filenames = [['foo.c',  'foo.c',                           'A/foo.c'],
               ['bar.c',   os.path.join('B', 'bar.c'),       'A/B/bar.c'],
               ['baf.c',   os.path.join('C', 'baf.c'),       'A/C/baf.c'],
               ['qux.c',   os.path.join('D', 'qux.c'),       'A/D/qux.c'],
               ['rip.bat', os.path.join('D', 'rip.bat'),     'A/D/rip.bat'],
               ['snk.py',  os.path.join('D', 'H', 'snk.py'), 'A/D/H/snk.py'],
               ['ric.c',   os.path.join('D', 'H', 'sir.c'),  'A/D/H/sir.c']]

  for filename in filenames:
    if cmd == 'import':
      svntest.main.file_write(os.path.join(files_dir, filename[0]),
                              'foo\nbar\nbaz\n')
    else:
      svntest.main.file_write(os.path.join(files_dir, filename[1]),
                              'foo\nbar\nbaz\n')

  if do_import_or_add:
    if len(subdir) == 0:
      # add/import the files
      for filename in filenames:
        if cmd == 'import':
          path = os.path.join(files_dir, filename[0])
          tmp_params = parameters + [path, repos_url + '/' + filename[2]]
        else:
          path = os.path.join(files_dir, filename[1])
          tmp_params = parameters + [path]
        svntest.main.run_svn(None, *tmp_params)
    else:
      # add/import subdirectory
      if cmd == 'import':
        parameters = parameters + [files_dir, repos_url]
      else:
        parameters = parameters + [files_wc_dir]
      svntest.main.run_svn(None, *parameters)

    # do an svn co if needed
    if cmd == 'import':
      svntest.main.run_svn(None, 'checkout', repos_url + '/A', files_wc_dir,
                          '--config-dir', config_dir)

    check_inheritable_autoprops(sbox, auto_props_cfg_enabled,
                                inheritable_auto_props_enabled)

  return config_dir

#----------------------------------------------------------------------

def svn_prop_inheritable_autoprops_add_no_none(sbox):
  "inherit add: config=no, commandline=none"
  inheritable_autoprops_test(sbox, 'add', False, 0, '')

#----------------------------------------------------------------------

def svn_prop_inheritable_autoprops_add_yes_none(sbox):
  "inherit add: config=yes,  commandline=none"
  inheritable_autoprops_test(sbox, 'add', True, 0, '')

#----------------------------------------------------------------------

def svn_prop_inheritable_autoprops_add_no_yes(sbox):
  "inherit add: config=no,  commandline=yes"

  inheritable_autoprops_test(sbox, 'add', 0, 1, '')

#----------------------------------------------------------------------

def svn_prop_inheritable_autoprops_add_yes_yes(sbox):
  "inherit add: config=yes, commandline=yes"

  inheritable_autoprops_test(sbox, 'add', 1, 1, '')

#----------------------------------------------------------------------

def svn_prop_inheritable_autoprops_add_no_no(sbox):
  "inherit add: config=no,  commandline=no"

  inheritable_autoprops_test(sbox, 'add', 0, -1, '')

#----------------------------------------------------------------------

def svn_prop_inheritable_autoprops_add_yes_no(sbox):
  "inherit add: config=yes, commandline=no"

  inheritable_autoprops_test(sbox, 'add', 1, -1, '')

#----------------------------------------------------------------------

def svn_prop_inheritable_autoprops_import_no_none(sbox):
  "inherit import: config=no, commandline=none"

  inheritable_autoprops_test(sbox, 'import', False, 0, '')

#----------------------------------------------------------------------

def svn_prop_inheritable_autoprops_imp_yes_none(sbox):
  "inherit import: config=yes, commandline=none"

  inheritable_autoprops_test(sbox, 'import', 1, 0, '')

#----------------------------------------------------------------------

def svn_prop_inheritable_autoprops_imp_no_yes(sbox):
  "inherit import: config=no,  commandline=yes"

  inheritable_autoprops_test(sbox, 'import', 0, 1, '')

#----------------------------------------------------------------------

def svn_prop_inheritable_autoprops_imp_yes_yes(sbox):
  "inherit import: config=yes, commandline=yes"

  inheritable_autoprops_test(sbox, 'import', 1, 1, '')

#----------------------------------------------------------------------

def svn_prop_inheritable_autoprops_imp_no_no(sbox):
  "inherit import: config=no,  commandline=no"

  inheritable_autoprops_test(sbox, 'import', 0, -1, '')

#----------------------------------------------------------------------

def svn_prop_inheritable_autoprops_imp_yes_no(sbox):
  "inherit import: config=yes, commandline=no"

  inheritable_autoprops_test(sbox, 'import', 1, -1, '')

#----------------------------------------------------------------------
# Test svn:auto-props when 'svn add' targets an already versioned
# target.
def svn_prop_inheritable_autoprops_add_versioned_target(sbox):
  "svn:auto-props and versioned target"

  config_dir = inheritable_autoprops_test(sbox, 'add', 1, 0, '', False)

  # Perform the add with the --force flag, and check the status.
  ### Note: You have to be inside the working copy or else Subversion
  ### will think you're trying to add the working copy to its parent
  ### directory, and will (possibly, if the parent directory isn't
  ### versioned) fail -- see also schedule_tests.py 11 "'svn add'
  ### should traverse already-versioned dirs"
  saved_wd = os.getcwd()
  os.chdir(sbox.wc_dir)
  svntest.main.run_svn(None, 'add', '.', '--force', '--config-dir',
                       config_dir)
  os.chdir(saved_wd)
  check_inheritable_autoprops(sbox, True, True)

  # Revert additions and try with --no-auto-props
  svntest.main.run_svn(None, 'revert', '-R', sbox.wc_dir)

  # When the add above sets svn:executable on D/rip.bat, subversion
  # also sets the execute bits on the file (on systems that support
  # that).  The revert above does not return the file to its original
  # permissions, so we do so manually now.  Otherwise the follwing
  # addition will notice the executable bits and set svn:executable
  # again, which is not what we are here to test.
  if os.name == 'posix':
    os.chmod(os.path.join(sbox.wc_dir, 'D', 'rip.bat'),
                          svntest.main.S_ALL_READ | stat.S_IWUSR | stat.S_IWGRP)

  os.chdir(sbox.wc_dir)
  svntest.main.run_svn(None, 'add', '.', '--force', '--no-auto-props',
                       '--config-dir', config_dir)
  os.chdir(saved_wd)
  check_inheritable_autoprops(sbox, False, False)

  # Create a new config with auto-props disabled.
  #
  # Then revert the previous additions and add again, only the
  # svn:auto-props should be applied.
  config_dir = create_inherited_autoprops_config(sbox, False)

  svntest.main.run_svn(None, 'revert', '-R', sbox.wc_dir)
  os.chdir(sbox.wc_dir)
  svntest.main.run_svn(None, 'add', '.', '--force',
                       '--config-dir', config_dir)
  os.chdir(saved_wd)
  check_inheritable_autoprops(sbox, False, True)

  # Revert  a final time and add again with the --auto-props switch.
  # Both the config defined and svn:auto-props should be applied.
  svntest.main.run_svn(None, 'revert', '-R', sbox.wc_dir)
  os.chdir(sbox.wc_dir)
  svntest.main.run_svn(None, 'add', '.', '--force', '--auto-props',
                       '--config-dir', config_dir)
  os.chdir(saved_wd)
  check_inheritable_autoprops(sbox, True, True)

#----------------------------------------------------------------------
# Can't set svn:auto-props on files.
def svn_prop_inheritable_autoprops_propset_file_target(sbox):
  "svn:auto-props can't be set on files"

  sbox.build()
  svntest.actions.run_and_verify_svn(
    None,
    ".*Cannot set '" + SVN_PROP_INHERITABLE_AUTOPROPS + "' on a file.*",
    'ps', SVN_PROP_INHERITABLE_AUTOPROPS, '*.c=svn:eol-style=native',
    sbox.ospath('iota'))

#----------------------------------------------------------------------
# Multiple unversioned subtrees under a versioned target shouldn't segfault.
def svn_prop_inheritable_autoprops_unversioned_subtrees_versioned_target(sbox):
  "versioned target and unversioned subtrees"

  sbox.build()
  Z_path = sbox.ospath('A/D/Z')
  Y_path = sbox.ospath('A/B/Y')
  foo_path = sbox.ospath('A/D/Z/foo.c')
  bar_path = sbox.ospath('A/B/Y/bar.c')

  # Set svn:auto-props properties on two directories.
  svntest.main.run_svn(None, 'ps', SVN_PROP_INHERITABLE_AUTOPROPS,
                       '*.c=svn:eol-style=CR', sbox.ospath('A/B'))
  svntest.main.run_svn(None, 'ps', SVN_PROP_INHERITABLE_AUTOPROPS,
                       '*.c=svn:eol-style=native', sbox.ospath('A/D'))
  sbox.simple_commit(message='Add inheritable autoprops')

  # Create two subtrees, each with one new file.
  os.mkdir(Z_path)
  os.mkdir(Y_path)
  svntest.main.file_write(foo_path,
                          '/* Someday there will be code here. */\n')
  svntest.main.file_write(bar_path,
                          '/* Someday there will be code here. */\n')

  # Perform the add with the --force flag, targeting the root of the WC.
  ### Note: You have to be inside the working copy or else Subversion
  ### will think you're trying to add the working copy to its parent
  ### directory, and will (possibly, if the parent directory isn't
  ### versioned) fail -- see also schedule_tests.py 11 "'svn add'
  ### should traverse already-versioned dirs"
  saved_wd = os.getcwd()
  os.chdir(sbox.wc_dir)
  # This was causing a segfault at one point.
  svntest.main.run_svn(None, 'add', '.', '--force')
  os.chdir(saved_wd)

  # Check the resulting autoprops.
  svntest.actions.run_and_verify_svn('native\n', [],
                                     'pg', 'svn:eol-style', foo_path)
  svntest.actions.run_and_verify_svn('CR\n', [],
                                     'pg', 'svn:eol-style', bar_path)

########################################################################
# Run the tests


# list all tests here, starting with None:
test_list = [ None,
              autoprops_add_no_none,
              autoprops_add_yes_none,
              autoprops_add_no_yes,
              autoprops_add_yes_yes,
              autoprops_add_no_no,
              autoprops_add_yes_no,
              autoprops_imp_no_none,
              autoprops_imp_yes_none,
              autoprops_imp_no_yes,
              autoprops_imp_yes_yes,
              autoprops_imp_no_no,
              autoprops_imp_yes_no,
              autoprops_add_dir,
              autoprops_imp_dir,
              fail_add_mixed_eol_style,
              svn_prop_inheritable_autoprops_add_no_none,
              svn_prop_inheritable_autoprops_add_yes_none,
              svn_prop_inheritable_autoprops_add_no_yes,
              svn_prop_inheritable_autoprops_add_yes_yes,
              svn_prop_inheritable_autoprops_add_no_no,
              svn_prop_inheritable_autoprops_add_yes_no,
              svn_prop_inheritable_autoprops_import_no_none,
              svn_prop_inheritable_autoprops_imp_yes_none,
              svn_prop_inheritable_autoprops_imp_no_yes,
              svn_prop_inheritable_autoprops_imp_yes_yes,
              svn_prop_inheritable_autoprops_imp_no_no,
              svn_prop_inheritable_autoprops_imp_yes_no,
              svn_prop_inheritable_autoprops_add_versioned_target,
              svn_prop_inheritable_autoprops_propset_file_target,
              svn_prop_inheritable_autoprops_unversioned_subtrees_versioned_target,
             ]

if __name__ == '__main__':
  svntest.main.run_tests(test_list)
  # NOTREACHED


### End of file.
