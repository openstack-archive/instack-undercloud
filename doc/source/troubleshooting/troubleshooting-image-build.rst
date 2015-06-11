Troubleshooting Image Build
===========================

Images fail to build
--------------------

More space needed
^^^^^^^^^^^^^^^^^

Images are built in tmpfs by default, to speed up the builds. In case
your machine doesn't have enough free RAM, the image building step
can fail with a message like "At least 174MB more space needed on
the / filesystem". If freeing up more RAM isn't a possibility,
images can be built on disk by exporting an environment variable::

    export DIB_NO_TMPFS=1
