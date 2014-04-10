Building RPM's
==============

instack-undercloud uses a tool called [tito](http://rm-rf.ca/tito) to aid in
building rpm's. You can install it via yum:

        sudo yum install tito

The specfile for instack-undercloud is committed to the root of this git
repository.

Most of what you need to know is in the tito documentation. What follows are
the main commands used for instack-undercloud.

To build a test rpm from the latest git commit in your local repository:

        tito build --rpm --test

The rpm is written to /tmp/tito. See the output from the above command for
the exact path. You can then copy the rpm around (e.g., over to your
undercloud) to test it out.


To tag a new release on master:

        tito tag
        git push origin master
        git push --tags

Note that this takes care of bumping the version in the specfile and generating
a ChangeLog entries for you in the specfile. Follow the prompts from tito for
applying the ChangeLog entries.


To build an rpm from the latest tag:

        tito build --rpm


To build an rpm in Fedora koji from the latest tag:

        tito release fedora-git

Note that you will need to be an Owner/CC of the package in Fedora dist-git.


To build a scratch build of an rpm in Fedora koji from the latest tag:

        tito release fedora-git --scratch
