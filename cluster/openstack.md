Can use `openstack-client` command line interface:
  `pip install python-openstackclient`

Then download the OpenStack RC file from nectar and source to set environment variables.

Docs: https://docs.openstack.org/python-openstackclient/latest/

Then can e.g.:
  `openstack image list` to list available compute images
  `openstack server create --image <image_id> --flavor <falvor_id> <name>` to create a compute instance
  `openstack container create/delete/list/save/set/show/unset` to work with containers

Need to use `openstack --os-cloud $CLOUD`, where $CLOUD is the name of the cloud in the `clouds.yaml` file

Also - need to create servers with a key name (e.g. 'alaroldai_haliax') - `openstack --os-cloud nectar --key-name alaroldai_haliax --image ... --flavor ... ...`

For ping / ssh to work, you'll also need to add the security appropriate security groups to the instance:
  `--security-group ssh --security-group icmp`

So the final command would be something like:
```sh
openstack --os-cloud nectar server create \
  --image 553190c0-5492-43df-ad98-fce3133a5eff \
  --flavor 71359ce0-49c8-4485-94ac-7936703c961b \
  --key-name alaroldai_haliax \
  --security-group ssh \
  --security-group icmp \
  test
```

Also - SSH will not work unless the originating machine is connected to the UniMelb VPN.
So the following setup is possible / preferred:
- Ferule: SSH to Haliax (VSCode / Terminal)
- Haliax: VPN to UniMelb
- Ferule via Haliax (SSH): SSH to OpenStack instance
  - Ansible etc.