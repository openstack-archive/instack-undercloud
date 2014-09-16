utility-image:
	imagefactory --debug base_image \
		--file-parameter install_script \
		utility_image.ks utility_image.tdl

input-image:
	imagefactory --debug base_image \
		--file-parameter install_script \
		input_image.ks input_image.tdl

overcloud-images: overcloud-control overcloud-compute overcloud-cinder-volume overcloud-swift-storage
	
overcloud-control:
	imagefactory --debug \
		target_image \
		--id $(INPUT_IMAGE_ID) \
		--parameter utility_image $(UTILITY_IMAGE_ID) \
		--file-parameter utility_customizations dib_overcloud_control.tdl \
		--parameter results_location "/overcloud-control.tar" indirection

overcloud-compute:
	imagefactory --debug \
		target_image \
		--id $(INPUT_IMAGE_ID) \
		--parameter utility_image $(UTILITY_IMAGE_ID) \
		--file-parameter utility_customizations dib_overcloud_compute.tdl \
		--parameter results_location "/overcloud-compute.tar" indirection

overcloud-cinder-volume:
	imagefactory --debug \
		target_image \
		--id $(INPUT_IMAGE_ID) \
		--parameter utility_image $(UTILITY_IMAGE_ID) \
		--file-parameter utility_customizations dib_overcloud_cinder_volume.tdl \
		--parameter results_location "/overcloud-cinder-volume.tar" indirection

overcloud-swift-storage:
	imagefactory --debug \
		target_image \
		--id $(INPUT_IMAGE_ID) \
		--parameter utility_image $(UTILITY_IMAGE_ID) \
		--file-parameter utility_customizations dib_overcloud_swift_storage.tdl \
		--parameter results_location "/overcloud-swift-storage.tar" indirection

deploy-ramdisk-ironic:
	imagefactory --debug \
		target_image \
		--id $(INPUT_IMAGE_ID) \
		--parameter utility_image $(UTILITY_IMAGE_ID) \
		--file-parameter utility_customizations dib_deploy_ramdisk_ironic.tdl \
		--parameter results_location "/deploy-ramdisk-ironic.tar" indirection

