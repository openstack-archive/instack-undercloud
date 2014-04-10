Building RPM's
==============

instack-undercloud uses a tool called [tito](http://rm-rf.ca/tito) to aid in
building rpm's. You can install it via yum:

        sudo yum install tito

The specfile for instack-undercloud is committed to the root of this git
repository.

Most of what you need to know is in the tito documentation. What follows are
the main commands used for instack-undercloud.

Releasing new builds
--------------------

First, tag a new release on master. This creates a git tag and takes care of bumping the version in the specfile and generatinga ChangeLog entries for you in the specfile. Follow the prompts from tito for
applying the ChangeLog entries.

        tito tag
        git push origin master
        git push --tags

Then build an rpm from the new tag for local testing.

        tito build --rpm


Then, build an rpm in Fedora koji from the new tag. Note that you will need to be an Owner/CC of the package in Fedora dist-git. This will update the sources in Fedora dist-git and perform a build in koji.

        tito release fedora-git

Note if you want to test some scratch builds first, you can use:

        tito release fedora-git --scratch
        
Build a test rpm
----------------
To build a test rpm from the latest git commit in your local repository:

        tito build --rpm --test

The rpm is written to /tmp/tito. See the output from the above command for
the exact path. You can then copy the rpm around (e.g., over to your
undercloud) to test it out.        
