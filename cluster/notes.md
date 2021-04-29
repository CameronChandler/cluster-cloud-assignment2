# Questions
- Do we need vms? nectar seems to support DB instances and containers...
  - But only MySql and Postgres
  - 

# Notes
Will need to ingest data from:
- Twitter
- AURIN (via https://aurin.org.au/aurin-apis)

Store data in CouchDB

Analysis via CouchDB's mapreduce capability

Infrastructure needs
- automatic scaling (docker swarm)
- automated deployment (ansible)

Suggested solution:
- Deploy VMs using the [OpenStack API](https://docs.openstack.org/api-quick-start/)
- Deploy VMs and install consul / docker using [Ansible](https://docs.ansible.com/)
- Build containers using [Docker](https://docs.docker.com/)
  - Note that we'll probably need a two-stage build process (build the target container from inside a build container), because build environments (MacOS, Windows) will differ from deployment environment (Linux / BSD)
- Deploy containers using docker swarm (`docker swarm join --advertise=<controller_node_ip> consul://<controller_node_ip>`)

# Instructions
Use `pipenv install`, then `pipenv shell` to enter a Python virtual environment with dependencies installed.
This will e.g. give access to the OpenStack command line tools, independent from other Python packages installed on your system.

Running `node-up.py` (`pipenv python node-up.py`) should:
  - Create two compute instances ('test' and 'test2') using the openstack command-line tools
  - Bootstrap Docker and Docker swarm on those instances

Dependencies:
- You'll need to download a `clouds.yaml` file for the Nectar project
  This can be found under Project -> API Access -> Download OpenStack RC File in the Nectar UI,
  and should be placed in your current working directory so that the openstack command-line tools can find it.
- You'll need to have set up a key pair in the Nectar UI (under Project -> Compute -> Key Pairs),
  and edit the builder constructed near the end of `node-up.py` to use the appropriate key pair.
  `node-up.py` will ask for the private key for that keypair and its passcode during its execution.
- Unless you store it in the OS_PASSWORD environment variable, `node-up.py` will also ask for
  your Nectar API password (found under settings -> Reset Password in the Nectar UI)
- Pay attention to the `heat/stack.yaml` file - this defines the resources deployed to OpenStack by `node-up.py`


Notes:
- Running this can be simplified by:
  - Storing your Nectar password in the OS_PASSWORD environment variable
  - Adding your SSH key passcode to the ssh agent ahead of time (see `man ssh-agent`, `man ssh-add`)

# Experiments
Using ansible ad-hoc commands to launch docker containers:

ansible -i ansible/generated_hosts.ini --become manager -a "docker service create --replicas 2 --name helloswarm alpine ping docker.com"

ansible -i ansible/generated_hosts.ini --become manager -a "docker service inspect --pretty helloswarm"


# TODO
- Setup up volumes for persistant storage
- Try running one-off programs in the docker swarm (more complex than ping)
