/*
 * util.c:
 * # ****************************************************************************
 * # TRASHY LITTLE SUBROUTINES
 * # ****************************************************************************
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

#include <apr_xml.h>
#include <apr_errno.h>
#include <apr_uri.h>
#include <apr_buckets.h>

#include <mod_dav.h>
#include <http_protocol.h>
#include <http_core.h>

#include "svn_error.h"
#include "svn_fs.h"
#include "svn_dav.h"
#include "svn_base64.h"
#include "svn_ctype.h"

#include "dav_svn.h"
#include "private/svn_fspath.h"
#include "private/svn_string_private.h"

dav_error *
dav_svn__new_error(apr_pool_t *pool,
                   int status,
                   int error_id,
                   apr_status_t aprerr,
                   const char *desc)
{
  if (error_id == 0)
    error_id = SVN_ERR_RA_DAV_REQUEST_FAILED;

/*
 * Note: dav_new_error() in httpd 2.0/2.2 always treated
 * the errno field in dav_error as an apr_status_t when
 * logging; on some platforms errno and apr_status_t
 * aren't directly interchangeable.  The code for httpd
 * > 2.2 below perpetuates this.
 */
#if AP_MODULE_MAGIC_AT_LEAST(20091119,0)
  return dav_new_error(pool, status, error_id, aprerr, desc);
#else

  errno = aprerr; /* For the same reason as in dav_svn__new_error_svn */

  return dav_new_error(pool, status, error_id, desc);
#endif
}

dav_error *
dav_svn__new_error_svn(apr_pool_t *pool,
                       int status,
                       int error_id,
                       apr_status_t aprerr,
                       const char *desc)
{
  if (error_id == 0)
    error_id = SVN_ERR_RA_DAV_REQUEST_FAILED;

#if AP_MODULE_MAGIC_AT_LEAST(20091119,0)
  return dav_new_error_tag(pool, status, error_id, aprerr,
                           desc, SVN_DAV_ERROR_NAMESPACE, SVN_DAV_ERROR_TAG);
#else
  /* dav_new_error_tag will record errno so we use it to pass aprerr.
     This overrwites any existing errno value but since Subversion
     makes no attempt to avoid system calls after a failed system call
     there is no guarantee that any existing errno represents a
     relevant error. */
  errno = aprerr;

  return dav_new_error_tag(pool, status, error_id, desc,
                           SVN_DAV_ERROR_NAMESPACE, SVN_DAV_ERROR_TAG);
#endif
}


/* Build up a chain of DAV errors that correspond to the underlying SVN
   errors that caused this problem. */
static dav_error *
build_error_chain(apr_pool_t *pool, svn_error_t *err, int status)
{
  char buffer[128];
  const char *msg = svn_err_best_message(err, buffer, sizeof(buffer));

  dav_error *derr = dav_svn__new_error_svn(pool, status, err->apr_err, 0,
                                           apr_pstrdup(pool, msg));

  if (err->child)
    derr->prev = build_error_chain(pool, err->child, status);

  return derr;
}


dav_error *
dav_svn__convert_err(svn_error_t *serr,
                     int status,
                     const char *message,
                     apr_pool_t *pool)
{
  dav_error *derr;

  /* Remove the trace-only error chain links.  We need predictable
     protocol behavior regardless of whether or not we're in a
     debugging build. */
  svn_error_t *purged_serr = svn_error_purge_tracing(serr);

  /* ### someday mod_dav_svn will send back 'rich' error tags, much
     finer grained than plain old svn_error_t's.  But for now, all
     svn_error_t's are marshalled to the client via the single
     generic <svn:error/> tag nestled within a <D:error> block. */

  /* Examine the Subverion error code, and select the most
     appropriate HTTP status code.  If no more appropriate HTTP
     status code maps to the Subversion error code, use the one
     suggested status provided by the caller. */
  switch (purged_serr->apr_err)
    {
    case SVN_ERR_FS_NOT_FOUND:
    case SVN_ERR_FS_NO_SUCH_REVISION:
      status = HTTP_NOT_FOUND;
      break;
    case SVN_ERR_UNSUPPORTED_FEATURE:
      status = HTTP_NOT_IMPLEMENTED;
      break;
    case SVN_ERR_FS_LOCK_OWNER_MISMATCH:
    case SVN_ERR_FS_PATH_ALREADY_LOCKED:
      status = HTTP_LOCKED;
      break;
    case SVN_ERR_FS_PROP_BASEVALUE_MISMATCH:
      status = HTTP_PRECONDITION_FAILED;
      break;
      /* add other mappings here */
    }

  derr = build_error_chain(pool, purged_serr, status);
  if (message != NULL
      && !svn_error_find_cause(purged_serr, SVN_ERR_REPOS_HOOK_FAILURE))
    /* Don't hide hook failures; we might hide the error text */
    derr = dav_push_error(pool, status, purged_serr->apr_err,
                          message, derr);

  /* Now, destroy the Subversion error. */
  svn_error_clear(serr);

  return derr;
}


/* Set *REVISION to the youngest revision in which an interesting
   history item (a modification, or a copy) occurred for PATH under
   ROOT.  Use POOL for scratchwork. */
static svn_error_t *
get_last_history_rev(svn_revnum_t *revision,
                     svn_fs_root_t *root,
                     const char *path,
                     apr_pool_t *pool)
{
  svn_fs_history_t *history;
  const char *ignored;

  /* Get an initial HISTORY baton. */
  SVN_ERR(svn_fs_node_history2(&history, root, path, pool, pool));

  /* Now get the first *real* point of interesting history. */
  SVN_ERR(svn_fs_history_prev2(&history, history, FALSE, pool, pool));

  /* Fetch the location information for this history step. */
  return svn_fs_history_location(&ignored, revision, history, pool);
}


svn_revnum_t
dav_svn__get_safe_cr(svn_fs_root_t *root, const char *path, apr_pool_t *pool)
{
  svn_revnum_t revision = svn_fs_revision_root_revision(root);
  svn_revnum_t history_rev;
  svn_fs_root_t *other_root;
  svn_fs_t *fs = svn_fs_root_fs(root);
  svn_fs_node_relation_t node_relation;
  svn_error_t *err;

  if ((err = get_last_history_rev(&history_rev, root, path, pool)))
    {
      svn_error_clear(err);
      return revision;   /* couldn't find last history rev */
    }

  if ((err = svn_fs_revision_root(&other_root, fs, history_rev, pool)))
    {
      svn_error_clear(err);
      return revision;   /* couldn't open the history rev */
    }

  if ((err = svn_fs_node_relation(&node_relation, root, path,
                                  other_root, path, pool)))
    {
      svn_error_clear(err);
      return revision;
    }

  if (node_relation == svn_fs_node_unchanged)
    return history_rev;  /* the history rev is safe!  the same node
                            exists at the same path in both revisions. */

  /* default */
  return revision;
}


const char *
dav_svn__build_uri(const dav_svn_repos *repos,
                   enum dav_svn__build_what what,
                   svn_revnum_t revision,
                   const char *path,
                   svn_boolean_t add_href,
                   apr_pool_t *pool)
{
  const char *root_path = repos->root_path;
  const char *special_uri = repos->special_uri;
  const char *path_uri = path ? svn_path_uri_encode(path, pool) : NULL;
  const char *href1 = add_href ? "<D:href>" : "";
  const char *href2 = add_href ? "</D:href>" : "";

  /* The first character of root_path is guaranteed to be "/".  If
     there's no component beyond that, then just use "", so that
     appending another "/" later does not result in "//". */
  if (root_path[1] == '\0')
    root_path = "";

  switch (what)
    {
    case DAV_SVN__BUILD_URI_ACT_COLLECTION:
      return apr_psprintf(pool, "%s%s/%s/act/%s",
                          href1, root_path, special_uri, href2);

    case DAV_SVN__BUILD_URI_BASELINE:
      return apr_psprintf(pool, "%s%s/%s/bln/%ld%s",
                          href1, root_path, special_uri, revision, href2);

    case DAV_SVN__BUILD_URI_BC:
      return apr_psprintf(pool, "%s%s/%s/bc/%ld/%s",
                          href1, root_path, special_uri, revision, href2);

    case DAV_SVN__BUILD_URI_PUBLIC:
      return apr_psprintf(pool, "%s%s%s%s",
                          href1, root_path, path_uri, href2);

    case DAV_SVN__BUILD_URI_VERSION:
      return apr_psprintf(pool, "%s%s/%s/ver/%ld%s%s",
                          href1, root_path, special_uri,
                          revision, path_uri, href2);

    case DAV_SVN__BUILD_URI_REVROOT:
      return apr_psprintf(pool, "%s%s/%s/rvr/%ld%s%s",
                          href1, root_path, special_uri,
                          revision, path_uri, href2);

    case DAV_SVN__BUILD_URI_VCC:
      return apr_psprintf(pool, "%s%s/%s/vcc/" DAV_SVN__DEFAULT_VCC_NAME "%s",
                          href1, root_path, special_uri, href2);

    default:
      /* programmer error somewhere */
      SVN_ERR_MALFUNCTION_NO_RETURN();
    }

  /* NOTREACHED */
}


svn_error_t *
dav_svn__simple_parse_uri(dav_svn__uri_info *info,
                          const dav_resource *relative,
                          const char *uri,
                          apr_pool_t *pool)
{
  apr_uri_t comp;
  const char *path;
  apr_size_t len1;
  apr_size_t len2;
  const char *slash;
  const char *created_rev_str;

  /* parse the input URI, in case it is more than just a path */
  if (apr_uri_parse(pool, uri, &comp) != APR_SUCCESS)
    goto malformed_uri;

  /* ### ignore all URI parts but the path (for now) */

  /* clean up the URI */
  if (comp.path == NULL)
    path = "/";
  else
    {
      ap_getparents(comp.path);
      ap_no2slash(comp.path);
      path = comp.path;
    }

  /*
   * Does the URI path specify the same repository? It does not if one of:
   *
   * 1) input is shorter than the path to our repository
   * 2) input is longer, but there is no separator
   *    [ http://host/repos vs http://host/repository ]
   * 3) the two paths do not match
   */
  len1 = strlen(path);
  len2 = strlen(relative->info->repos->root_path);
  if (len2 == 1 && relative->info->repos->root_path[0] == '/')
    len2 = 0;

  if (len1 < len2
      || (len1 > len2 && path[len2] != '/')
      || memcmp(path, relative->info->repos->root_path, len2) != 0)
    {
      return svn_error_create(SVN_ERR_APMOD_MALFORMED_URI, NULL,
                              "Unusable URI: it does not refer to this "
                              "repository");
    }

  /* prep the return value */
  memset(info, 0, sizeof(*info));
  info->rev = SVN_INVALID_REVNUM;

  path += len2; /* now points to "/" or "\0" */
  len1 -= len2;

  if (len1 <= 1)
    {
      info->repos_path = "/";
      return NULL;
    }

  /* skip over the leading "/" */
  ++path;
  --len1;

  /* is this a special URI? */
  len2 = strlen(relative->info->repos->special_uri);
  if (len1 < len2
      || (len1 > len2 && path[len2] != '/')
      || memcmp(path, relative->info->repos->special_uri, len2) != 0)
    {
      /* this is an ordinary "public" URI, so back up to include the
         leading '/' and just return... no need to parse further. */
      info->repos_path = svn_path_uri_decode(path - 1, pool);
      return NULL;
    }

  path += len2; /* now points to "/" or "\0" just past the special URI */
  len1 -= len2;

  /* ### we don't handle the root of the special area yet */
  if (len1 <= 1)
    goto unhandled_form;

  /* Find the next component, and ensure something is there. */
  slash = ap_strchr_c(path + 1, '/');
  if (slash == NULL || slash[1] == '\0')
    goto unhandled_form;
  len2 = slash - path;

  /* Figure out what we have here */
  if (len2 == 4 && memcmp(path, "/act/", 5) == 0)
    {
      /* an activity */
      info->activity_id = path + 5;
    }
  else if (len2 == 4 &&
           (memcmp(path, "/ver/", 5) == 0 || memcmp(path, "/rvr/", 5) == 0))
    {
      /* a version resource */
      path += 5;
      len1 -= 5;
      slash = ap_strchr_c(path, '/');
      if (slash == NULL)
        {
          created_rev_str = apr_pstrndup(pool, path, len1);
          info->rev = SVN_STR_TO_REV(created_rev_str);
          info->repos_path = "/";
        }
      else
        {
          created_rev_str = apr_pstrndup(pool, path, slash - path);
          info->rev = SVN_STR_TO_REV(created_rev_str);
          info->repos_path = svn_path_uri_decode(slash, pool);
        }
      if (info->rev == SVN_INVALID_REVNUM)
        goto malformed_uri;
    }
  else
    goto unhandled_form;

  return NULL;

 malformed_uri:
    return svn_error_create(SVN_ERR_APMOD_MALFORMED_URI, NULL,
                            "The specified URI could not be parsed");

 unhandled_form:
  return svn_error_create(SVN_ERR_UNSUPPORTED_FEATURE, NULL,
                          "Unsupported URI form");
}

svn_boolean_t
dav_svn__is_parentpath_list(request_rec *r)
{
  const char *fs_parent_path = dav_svn__get_fs_parent_path(r);

  if (fs_parent_path && dav_svn__get_list_parentpath_flag(r))
    {
      const char *root_path = dav_svn__get_root_dir(r);
      char *uri = apr_pstrdup(r->pool, r->uri);
      char *parentpath = apr_pstrdup(r->pool, root_path);
      apr_size_t uri_len = strlen(uri);
      apr_size_t parentpath_len = strlen(parentpath);

      if (uri[uri_len-1] == '/')
        uri[uri_len-1] = '\0';

      if (parentpath[parentpath_len-1] == '/')
        parentpath[parentpath_len-1] = '\0';

      if (strcmp(parentpath, uri) == 0)
        {
          return TRUE;
        }
    }
  return FALSE;
}

/* ### move this into apr_xml */
int
dav_svn__find_ns(const apr_array_header_t *namespaces, const char *uri)
{
  int i;

  for (i = 0; i < namespaces->nelts; ++i)
    if (strcmp(APR_XML_GET_URI_ITEM(namespaces, i), uri) == 0)
      return i;
  return -1;
}


/*** Output helpers ***/


struct dav_svn__output
{
  request_rec *r;
};

dav_svn__output *
dav_svn__output_create(request_rec *r,
                       apr_pool_t *pool)
{
  dav_svn__output *output = apr_pcalloc(pool, sizeof(*output));
  output->r = r;
  return output;
}

apr_bucket_alloc_t *
dav_svn__output_get_bucket_alloc(dav_svn__output *output)
{
  return output->r->connection->bucket_alloc;
}

svn_error_t *
dav_svn__output_pass_brigade(dav_svn__output *output,
                             apr_bucket_brigade *bb)
{
  apr_status_t status;

  status = ap_pass_brigade(output->r->output_filters, bb);
  /* Empty the brigade here, as required by ap_pass_brigade(). */
  apr_brigade_cleanup(bb);
  if (status)
    return svn_error_create(status, NULL, "Could not write data to filter");

  /* Check for an aborted connection, since the brigade functions don't
     appear to return useful errors when the connection is dropped. */
  if (output->r->connection->aborted)
    return svn_error_create(SVN_ERR_APMOD_CONNECTION_ABORTED, NULL, NULL);
  return SVN_NO_ERROR;
}


/*** Brigade I/O wrappers ***/


svn_error_t *
dav_svn__brigade_write(apr_bucket_brigade *bb,
                       dav_svn__output *output,
                       const char *data,
                       apr_size_t len)
{
  apr_status_t apr_err;
  apr_err = apr_brigade_write(bb, ap_filter_flush,
                              output->r->output_filters, data, len);
  if (apr_err)
    return svn_error_create(apr_err, 0, NULL);
  /* Check for an aborted connection, since the brigade functions don't
     appear to return useful errors when the connection is dropped. */
  if (output->r->connection->aborted)
    return svn_error_create(SVN_ERR_APMOD_CONNECTION_ABORTED, 0, NULL);
  return SVN_NO_ERROR;
}


svn_error_t *
dav_svn__brigade_puts(apr_bucket_brigade *bb,
                      dav_svn__output *output,
                      const char *str)
{
  apr_status_t apr_err;
  apr_err = apr_brigade_puts(bb, ap_filter_flush,
                             output->r->output_filters, str);
  if (apr_err)
    return svn_error_create(apr_err, 0, NULL);
  /* Check for an aborted connection, since the brigade functions don't
     appear to return useful errors when the connection is dropped. */
  if (output->r->connection->aborted)
    return svn_error_create(SVN_ERR_APMOD_CONNECTION_ABORTED, 0, NULL);
  return SVN_NO_ERROR;
}


svn_error_t *
dav_svn__brigade_printf(apr_bucket_brigade *bb,
                        dav_svn__output *output,
                        const char *fmt,
                        ...)
{
  apr_status_t apr_err;
  va_list ap;

  va_start(ap, fmt);
  apr_err = apr_brigade_vprintf(bb, ap_filter_flush,
                                output->r->output_filters, fmt, ap);
  va_end(ap);
  if (apr_err)
    return svn_error_create(apr_err, 0, NULL);
  /* Check for an aborted connection, since the brigade functions don't
     appear to return useful errors when the connection is dropped. */
  if (output->r->connection->aborted)
    return svn_error_create(SVN_ERR_APMOD_CONNECTION_ABORTED, 0, NULL);
  return SVN_NO_ERROR;
}


svn_error_t *
dav_svn__brigade_putstrs(apr_bucket_brigade *bb,
                         dav_svn__output *output,
                         ...)
{
  apr_status_t apr_err;
  va_list ap;

  va_start(ap, output);
  apr_err = apr_brigade_vputstrs(bb, ap_filter_flush,
                                 output->r->output_filters, ap);
  va_end(ap);
  if (apr_err)
    return svn_error_create(apr_err, NULL, NULL);
  /* Check for an aborted connection, since the brigade functions don't
     appear to return useful errors when the connection is dropped. */
  if (output->r->connection->aborted)
    return svn_error_create(SVN_ERR_APMOD_CONNECTION_ABORTED, NULL, NULL);
  return SVN_NO_ERROR;
}




dav_error *
dav_svn__test_canonical(const char *path, apr_pool_t *pool)
{
  if (path[0] == '\0')
    return NULL;
  if (svn_path_is_url(path) && svn_uri_is_canonical(path, pool))
    return NULL;
  if ((path[0] == '/') && svn_fspath__is_canonical(path))
    return NULL;
  if (svn_relpath_is_canonical(path))
    return NULL;

  /* Otherwise, generate a generic HTTP_BAD_REQUEST error. */
  return dav_svn__new_error_svn(
     pool, HTTP_BAD_REQUEST, 0, 0,
     apr_psprintf(pool,
                  "Path '%s' is not canonicalized; "
                  "there is a problem with the client.", path));
}


dav_error *
dav_svn__sanitize_error(svn_error_t *serr,
                        const char *new_msg,
                        int http_status,
                        request_rec *r)
{
  svn_error_t *safe_err = serr;
  if (new_msg != NULL)
    {
      /* Purge error tracing from the error chain. */
      svn_error_t *purged_serr = svn_error_purge_tracing(serr);

      /* Sanitization is necessary.  Create a new, safe error and
           log the original error. */
      safe_err = svn_error_create(purged_serr->apr_err, NULL, new_msg);
      ap_log_rerror(APLOG_MARK, APLOG_ERR, APR_EGENERAL, r,
                    "%s", purged_serr->message);

      /* Log the entire error chain. */
      while (purged_serr->child)
        {
          purged_serr = purged_serr->child;
          ap_log_rerror(APLOG_MARK, APLOG_ERR, APR_EGENERAL, r,
                        "%s", purged_serr->message);
        }

      svn_error_clear(serr);
    }

  return dav_svn__convert_err(safe_err, http_status,
                              apr_psprintf(r->pool, "%s", safe_err->message),
                              r->pool);
}


struct brigade_write_baton
{
  apr_bucket_brigade *bb;
  dav_svn__output *output;
};


/* This implements 'svn_write_fn_t'. */
static svn_error_t *
brigade_write_fn(void *baton, const char *data, apr_size_t *len)
{
  struct brigade_write_baton *wb = baton;
  apr_status_t apr_err;

  apr_err = apr_brigade_write(wb->bb, ap_filter_flush,
                              wb->output->r->output_filters, data, *len);

  if (apr_err != APR_SUCCESS)
    return svn_error_wrap_apr(apr_err, "Error writing base64 data");

  return SVN_NO_ERROR;
}


svn_stream_t *
dav_svn__make_base64_output_stream(apr_bucket_brigade *bb,
                                   dav_svn__output *output,
                                   apr_pool_t *pool)
{
  struct brigade_write_baton *wb = apr_palloc(pool, sizeof(*wb));
  svn_stream_t *stream = svn_stream_create(wb, pool);

  wb->bb = bb;
  wb->output = output;
  svn_stream_set_write(stream, brigade_write_fn);

  return svn_base64_encode2(stream, FALSE, pool);
}

void
dav_svn__operational_log(struct dav_resource_private *info, const char *line)
{
  apr_table_set(info->r->subprocess_env, "SVN-ACTION", line);
  apr_table_set(info->r->subprocess_env, "SVN-REPOS",
                svn_path_uri_encode(info->repos->fs_path, info->r->pool));
  apr_table_set(info->r->subprocess_env, "SVN-REPOS-NAME",
                svn_path_uri_encode(info->repos->repo_basename, info->r->pool));
}


dav_error *
dav_svn__final_flush_or_error(request_rec *r,
                              apr_bucket_brigade *bb,
                              dav_svn__output *output,
                              dav_error *preferred_err,
                              apr_pool_t *pool)
{
  dav_error *derr = preferred_err;
  svn_boolean_t do_flush;

  do_flush = r->sent_bodyct > 0;
  if (! do_flush)
    {
      /* Ask about the length of the bucket brigade, ignoring errors. */
      apr_off_t len = 0;
      (void)apr_brigade_length(bb, FALSE, &len);
      do_flush = (len != 0);
    }

  /* If there's something in the bucket brigade to flush, or we've
     already started sending data down the wire, flush what we've
     got.  We only keep any error retrieved from the flush if weren't
     provided a more-important DERR, though. */
  if (do_flush)
    {
      apr_status_t apr_err = ap_fflush(output->r->output_filters, bb);
      if (apr_err && (! derr))
        derr = dav_svn__new_error(pool, HTTP_INTERNAL_SERVER_ERROR, 0, apr_err,
                                  "Error flushing brigade.");
    }
  return derr;
}

void dav_svn__log_err(request_rec *r,
                      dav_error *err,
                      int level)
{
    dav_error *errscan;

    /* Log the errors */
    /* ### should have a directive to log the first or all */
    for (errscan = err; errscan != NULL; errscan = errscan->prev) {
        apr_status_t status;

        if (errscan->desc == NULL)
            continue;

#if AP_MODULE_MAGIC_AT_LEAST(20091119,0)
        status = errscan->aprerr;
#else
        status = errscan->save_errno;
#endif

        ap_log_rerror(APLOG_MARK, level, status, r,
                      "%s  [%d, #%d]",
                      errscan->desc, errscan->status, errscan->error_id);
    }
}

int
dav_svn__error_response_tag(request_rec *r,
                            dav_error *err)
{
  r->status = err->status;

  /* ### I really don't think this is needed; gotta test */
  r->status_line = ap_get_status_line(err->status);

  ap_set_content_type(r, DAV_XML_CONTENT_TYPE);
  ap_rputs(DAV_XML_HEADER DEBUG_CR "<D:error xmlns:D=\"DAV:\"", r);

  if (err->desc != NULL)
    ap_rputs(" xmlns:m=\"http://apache.org/dav/xmlns\"", r);

  if (err->namespace != NULL)
    ap_rprintf(r, " xmlns:C=\"%s\">" DEBUG_CR "<C:%s/>" DEBUG_CR,
               err->namespace, err->tagname);
  else if (err->tagname != NULL)
    ap_rprintf(r, ">" DEBUG_CR "<D:%s/>" DEBUG_CR, err->tagname);
  else
    ap_rputs(">" DEBUG_CR, r);

  /* here's our mod_dav specific tag: */
  if (err->desc != NULL)
    ap_rprintf(r, "<m:human-readable errcode=\"%d\">" DEBUG_CR "%s" DEBUG_CR
               "</m:human-readable>" DEBUG_CR, err->error_id,
               apr_xml_quote_string(r->pool, err->desc, 0));

  ap_rputs("</D:error>" DEBUG_CR, r);

  /* the response has been sent. */
  /*
   * ### Use of DONE obviates logging..!
   */
  return DONE;
}


/* Set *REQUEST_STR to a string containing the contents of the body of
   request R, allocated from POOL.

   NOTE: This was shamelessly stolen and modified from Apache's
   ap_xml_parse_input().  */
static int
request_body_to_string(svn_string_t **request_str,
                       request_rec *r,
                       apr_pool_t *pool)
{
  apr_bucket_brigade *brigade;
  int seen_eos;
  apr_status_t status;
  apr_off_t total_read = 0;
  apr_off_t limit_req_body = ap_get_limit_xml_body(r);
  int result = HTTP_BAD_REQUEST;
  const char *content_length_str;
  char *endp;
  apr_off_t content_length;
  svn_stringbuf_t *buf;

  *request_str = NULL;

  content_length_str = apr_table_get(r->headers_in, "Content-Length");
  if (content_length_str)
    {
      if (apr_strtoff(&content_length, content_length_str, &endp, 10)
          || endp == content_length_str || *endp || content_length < 0)
        {
          ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r, "Invalid Content-Length");
          return HTTP_REQUEST_ENTITY_TOO_LARGE;
        }
    }
  else
    content_length = 0;

  if (limit_req_body && (limit_req_body < content_length))
    {
      ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r,
                    "Requested content-length of %" APR_OFF_T_FMT " is larger "
                    "than the configured limit of %" APR_OFF_T_FMT,
                    content_length, limit_req_body);
      return HTTP_REQUEST_ENTITY_TOO_LARGE;
    }

  if (content_length)
    {
      /* Do not allocate more than 1 MB until we receive request body. */
      apr_size_t alloc_len = 1 * 1024 *1024;
      if (content_length < alloc_len)
        alloc_len = (apr_size_t) content_length;

      buf = svn_stringbuf_create_ensure(alloc_len, pool);
    }
  else
    {
      buf = svn_stringbuf_create_empty(pool);
    }

  brigade = apr_brigade_create(r->pool, r->connection->bucket_alloc);
  seen_eos = 0;
  total_read = 0;

  do
    {
      apr_bucket *bucket;

      status = ap_get_brigade(r->input_filters, brigade, AP_MODE_READBYTES,
                              APR_BLOCK_READ, 2048);
      if (status != APR_SUCCESS)
        goto cleanup;

      for (bucket = APR_BRIGADE_FIRST(brigade);
           bucket != APR_BRIGADE_SENTINEL(brigade);
           bucket = APR_BUCKET_NEXT(bucket))
        {
          const char *data;
          apr_size_t len;

          if (APR_BUCKET_IS_EOS(bucket))
            {
              seen_eos = 1;
              break;
            }

          if (APR_BUCKET_IS_METADATA(bucket))
            continue;

          status = apr_bucket_read(bucket, &data, &len, APR_BLOCK_READ);
          if (status != APR_SUCCESS)
            goto cleanup;

          total_read += len;
          if (limit_req_body && total_read > limit_req_body)
            {
              ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r,
                            "Request body is larger than the configured "
                            "limit of %" APR_OFF_T_FMT, limit_req_body);
              result = HTTP_REQUEST_ENTITY_TOO_LARGE;
              goto cleanup;
            }

          svn_stringbuf_appendbytes(buf, data, len);
        }

      apr_brigade_cleanup(brigade);
    }
  while (!seen_eos);

  apr_brigade_destroy(brigade);

  /* Make an svn_string_t from our svn_stringbuf_t. */
  *request_str = svn_stringbuf__morph_into_string(buf);
  return OK;

 cleanup:
  apr_brigade_destroy(brigade);

  /* Apache will supply a default error, plus the error log above. */
  return result;
}

int
dav_svn__parse_request_skel(svn_skel_t **skel,
                            request_rec *r,
                            apr_pool_t *pool)
{
  svn_string_t *skel_str;
  int status;

  *skel = NULL;
  status = request_body_to_string(&skel_str, r, pool);
  if (status != OK)
    return status;

  *skel = svn_skel__parse(skel_str->data, skel_str->len, pool);
  return OK;
}

svn_error_t *
dav_svn__get_youngest_rev(svn_revnum_t *youngest_p,
                          dav_svn_repos *repos,
                          apr_pool_t *scratch_pool)
{
  if (repos->youngest_rev == SVN_INVALID_REVNUM)
    {
      svn_revnum_t revnum;
      SVN_ERR(svn_fs_youngest_rev(&revnum, repos->fs, scratch_pool));
      repos->youngest_rev = revnum;
    }

   *youngest_p = repos->youngest_rev;
   return SVN_NO_ERROR;
}

const char *
dav_svn__fuzzy_escape_author(const char *author,
                             svn_boolean_t is_svn_client,
                             apr_pool_t *result_pool,
                             apr_pool_t *scratch_pool)
{
  apr_size_t len = strlen(author);
  if (is_svn_client && !svn_xml_is_xml_safe(author, len))
    {
      /* We are talking to a Subversion client, which will (like any proper
         xml parser) error out if we produce control characters in XML.

         However Subversion clients process both the generic
         <creator-displayname /> as the custom element for svn:author.

         Let's skip outputting the invalid characters here to make the XML
         valid, so clients can see the custom element.

         Subversion Clients will then either use a slightly invalid
         author (unlikely) or more likely use the second result, which
         will be transferred with full escaping capabilities.

         We have tests in place to assert proper behavior over the RA layer.
       */
      apr_size_t i;
      svn_stringbuf_t *buf;

      buf = svn_stringbuf_ncreate(author, len, scratch_pool);

      for (i = 0; i < buf->len; i++)
        {
          char c = buf->data[i];

          if (svn_ctype_iscntrl(c))
            {
              svn_stringbuf_remove(buf, i--, 1);
            }
        }

      author = buf->data;
    }

  return apr_xml_quote_string(result_pool, author, 1);
}
