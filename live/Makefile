iso:
	livemedia-creator \
		--ks instack.ks \
		--make-iso \
		--iso /storage/isos/Fedora-20-x86_64-netinst.iso \
		--proxy http://192.168.122.1:3128 \
		--tmp .

appliance:
	livemedia-creator \
		--ks instack.ks \
		--iso /storage/isos/Fedora-20-x86_64-netinst.iso \
		--proxy http://192.168.122.1:3128 \
		--make-appliance \
		--tmp .

iso-source:
	livemedia-creator \
		--ks instack-source-livecd.ks \
		--make-iso \
		--iso /storage/isos/Fedora-20-x86_64-netinst.iso \
		--proxy http://192.168.122.1:3128 \
		--title "OpenStack Management Title" \
		--project "OpenStack Management Fedora" \
		--releasever 20 \
		--tmp .

appliance-source:
	livemedia-creator \
		--ks instack-source-livecd.ks \
		--iso /storage/isos/Fedora-20-x86_64-netinst.iso \
		--proxy http://192.168.122.1:3128 \
		--make-appliance \
		--tmp .
