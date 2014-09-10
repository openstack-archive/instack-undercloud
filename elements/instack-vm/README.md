Build an instack vm image

This element allows building an instack vm image using diskimage-builder. To build
the image simply include this element and the appropriate distro element.
For example:

disk-image-create -a amd64 -o instack \
    --image-size 30 \
    fedora instack-vm