/*
 * proxy.swg :  SWIG include file for defining automatic proxy classes
 *
 * ====================================================================
 *    Licensed to the Apache Software Foundation (ASF) under one
 *    or more contributor license agreements.  See the NOTICE file
 *    distributed with this work for additional information
 *    regarding copyright ownership.  The ASF licenses this file
 *    to you under the Apache License, Version 2.0 (the
 *    "License"); you may not use this file except in compliance
 *    with the License.  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing,
 *    software distributed under the License is distributed on an
 *    "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 *    KIND, either express or implied.  See the License for the
 *    specific language governing permissions and limitations
 *    under the License.
 * ====================================================================
 */

#ifdef SWIGPYTHON

/* Note: See the big comment at the top of proxy_apr.swg for details on
 *       how this _is_valid stuff actually works.  It's part of the magic
 *       that lets us gracefully handle objects that are allocated from
 *       a pool that's been cleared or destroyed.
 */
 
%pythoncode %{
  def _copy_metadata_deep(value, old_value):
    """Copy all attributes of old_value into value, recursively traversing
    lists and dicts if needed."""
    if value is None or old_value is None or value is old_value: return
    
    if isinstance(value, dict):
      for k in value:
        _copy_metadata_deep(value[k], old_value[k])
    elif isinstance(value, list):
      for v, old_v in zip(value, old_value):
        _copy_metadata_deep(v, old_v)
    else:
      try:
        value.__dict__.update(old_value.__dict__)
      except AttributeError:
        pass
        
  def _assert_valid_deep(value):
    """Assert value's validity, recursively traversing lists and dicts."""
    if isinstance(value, dict):
      for k in value:
        _assert_valid_deep(value[k])
    elif isinstance(value, list):
      for v in value:
        _assert_valid_deep(v)
    # Ensure that the passed in value isn't a type, which could have an
    # assert_valid attribute, but it can not be called without an instance.
    elif type(value) != type:
      try:
        fn = value.assert_valid
      except AttributeError:
        pass
      else:
        fn()

%}
#if SWIG_VERSION >= 0x040000
%pythoncode %{
  # -classic and -modern options have been dropped and this variable
  # is not generated since SWIG 4
  _newclass = 1
  _get_instance_attr = object.__getattribute__
  _set_instance_attr = _swig_setattr_nondynamic_instance_variable(object.__setattr__)

%}
#elif defined(SWIGPYTHON_PY3)
%pythoncode %{
  # SWIG classes generated with -modern do not define this variable
  try:
    _newclass
  except NameError:
    _newclass = 1
  else:
    raise RuntimeError("Require -modern option, but _newclass is defined")

  _get_instance_attr = object.__getattribute__
  _set_instance_attr = _swig_setattr_nondynamic_method(object.__setattr__)

%}
#else
%pythoncode %{
  # SWIG classes generated with -classic do not define this variable,
  # so set it to 0 when it doesn't exist
  try:
    _newclass
  except NameError:
    _newclass = 0

  if _newclass:
    def _get_instance_attr(self, name):
      try:
        return object.__getattribute__(self, name)
      except AttributeError:
        return _swig_getattr(self, object.__getattribute__(self, '__class__'),
                             name)
  else:
    def _get_instance_attr(self, name):
      return _swig_getattr(self, self.__class__, name)

  def _set_instance_attr(self, name, value):
    return _swig_setattr(self, self.__class__, name, value)

%}
#endif

/* Default code for all wrapped proxy classes in Python.
 * Inline the code from a separate file to avoid issues with
 * SWIG mis-parsing the comments as preprocessor directives. */
%define %proxy_pythoncode(TYPE)
%pythoncode "proxy.py"
%enddef

/* Define a proxy for wrapping an existing struct */
%define %proxy(TYPE)
%extend TYPE {
%proxy_pythoncode(TYPE);
}
%enddef

/* Define a proxy class for wrapping an opaque struct */
%define %opaque_proxy(TYPE)
struct TYPE {
%extend {
%proxy_pythoncode(TYPE);
}
}
%enddef

/* Treat typemapped function pointers as objects, which have a bound
 * __call__ method. This mapping depends on the function pointer being
 * typemapped as a CALLABLE_CALLBACK. */
%define %funcptr_proxy(TYPE, INVOKE)
%nodefault TYPE;
struct TYPE {
%extend {
%proxy_pythoncode(TYPE);
%pythoncode %{
  def __call__(self, *args):
    return INVOKE(self, *args)
%}
}
};

%enddef

/* Add member functions to objects so that their function pointers can
 * be invoked.
 *
 * Unlike the CALLABLE_CALLBACKS, these member functions don't have or
 * need typemaps, because the underlying C/SWIG object for the callback
 * is hidden.
 */
%define %funcptr_member_proxy(TYPE, MEMBER, INVOKE)
%extend TYPE {
%pythoncode %{
  def MEMBER(self, *args):
    return INVOKE(self, *args)
%}
}
%enddef


#endif
