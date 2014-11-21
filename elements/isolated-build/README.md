Build images isolated from any external sources of software.

This is necessary for doing builds in things like Koji and Brew,
where only installation sources known to the build system are
allowed.  This element enables that by removing/blacklisting
Git and Pip and disabling source repositories.

Note that this method is not perfect - it's still possible for
Git or Pip to be pulled in as a dependency of another package,
but since currently this requirement is on a best-effort basis
this is our best effort to meet it.  At some point this will be
enforced by the build system itself and we won't be responsible
for ensuring compliance.
