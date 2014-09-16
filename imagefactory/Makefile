utility-image:
	imagefactory --debug base_image \
		--file-parameter install_script \
		utility_image.ks utility_image.tdl

input-image:
	imagefactory --debug base_image \
		--file-parameter install_script \
		input_image.ks input_image.tdl

overcloud-compute:
	imagefactory --debug \
		target_image \
		--id $(INPUT_IMAGE_ID) \
		--parameter utility_image $(UTILITY_IMAGE_ID) \
		--file-parameter utility_customizations dib_overcloud_compute.tdl \
		--parameter results_location "/overcloud-compute.tar" indirection

