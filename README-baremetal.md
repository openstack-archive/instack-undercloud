The NODES_JSON file specified in the deploy-overcloudrc file should be in the
following format:

For virt:

        {
          "nodes":
            [
              {
                "memory": "4072",
                "disk": "30",
                "arch": "x86_64",
                "pm_user": "stack",
                "pm_addr": "192.168.122.1",
                "pm_password": "contents of ssh private key go here",
                "pm_type": "pxe_ssh",
                "mac": [
                  "00:76:31:1f:f2:a0"
                ],
                "cpu": "1"
              },
              {
                "memory": "4072",
                "disk": "30",
                "arch": "x86_64",
                "pm_user": "stack",
                "pm_addr": "192.168.122.1",
                "pm_password": "contents of ssh private key go here",
                "pm_type": "pxe_ssh",
                "mac": [
                  "00:76:31:1f:f2:a0"
                ],
                "cpu": "1"
              }
            ]
        }

For baremetal:

        {
          "nodes": [
            {
              "pm_password": "ipmi password goes here",
              "pm_type": "pxe_ipmitool",
              "mac": [
                "ipmi mac address goes here"
              ],
              "cpu": "4",
              "memory": "32768",
              "disk": "900",
              "arch": "x86_64",
              "pm_user": "ipmi username goes here",
              "pm_addr": "ipmi ip address goes here"
            },
            {
              "pm_password": "ipmi password goes here",
              "pm_type": "pxe_ipmitool",
              "mac": [
                "ipmi mac address goes here"
              ],
              "cpu": "4",
              "memory": "32768",
              "disk": "900",
              "arch": "x86_64",
              "pm_user": "ipmi username goes here",
              "pm_addr": "ipmi ip address goes here"
            }
          ]
        }


