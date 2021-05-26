# COMP90024 Team 54 - Literacy Analysis

# User Guide
A simple user guide for testing, including system deployment and end user invocation/usage of the systems.

## Using `node\_up.py`

### Script inputs
The system can be set up by running the `node_up.py` script. This script runs through the steps required for configuration and deployment of the elements in the system. Arguments that the user needs to pass into the script are the following:

```--os-cloud, default='nectar-private'```

The `os-cloud` argument refers to which cloud project we choose to use. The options are one of the projects defined in `clouds.yaml` file.


```--os-stack, default='stack'```

The `os-stack` argument refers to the name of the OpenStack stack that is to be created on the user's cloud.

```--os-keypair-name```

The `os-keypair-name` argument does not have a default value and always have to be specified by the user. It refers to the key pair name in their Nectar cloud.

```--os-keypair-path, default='~/.ssh/id_rsa'```

The `os-keypair-name` argument refers to the path to the user's private key in their local computer. It should be able to match with the public key in their Nectar cloud with the `os-keypair-name` specified above.

```
--couch-user, default='admin'
--couch-password, default='<default password>'
```

The `couch-user` and `couch-password` arguments set up the username and password required to access to the CouchDB instance to be deployed.


```--couch-secret, default='<default secret>'```

Each CouchDB cluster needs to have their own `couch-secret`. It serves as an additional safeguard against malicious users taking control of the CouchDB cluster.

For example, if the user's key pair name in their Nectar cloud is `my-name`, an example of a command line to run `node-up.py` would be:

```python3 node-up.py --os-keypair-name my-name```


In addition to the command-line arguments, the script makes use of the OpenStack command-line interface, and requires that a file named `clouds.yaml` that contains details for the used OpenStack project  is present in the working directory.

There are several other inputs the script may ask for, including a password for OpenStack authentication, and the password for the private key that is used to connect to nodes in the cluster. For quality-of-life, we recommend setting the former as an environment variable (the script will use the value of `OS_PASSWORD` if it is set), and using an `ssh agent` session to manage private key credentials.

The script will be up and running after the command. At each step in the script, the user will be prompted to input whether or not they want to execute that step. Details about these steps are in the following section.

### The execution steps
The script contains classes that encapsulate details about the configuration of each element by specifying what value the variables take. It also contains kernel commands that will execute the set up or installation of the elements. The elements include OpenStack, Docker, and CouchDB. Elements such as Frontend, Backend, and Twitter Harvester are deployed as Docker containers as part of the execution of the script.

After setting up the required configurations for OpenStack, Docker and CouchDB, an Orchestrator instance is created to interact with the configured machines. The Orchestrator first checks if an OpenStack stack already exists with the name by using the OpenStack CLI to fetch the list of deployed stacks. It will then either update the existing stack or create a new one accordingly. The IP addresses of the VMs created from stack creation is retrieved from the output of the stack creation process to ensure its correctness. This IP address is needed to write a hosts file for Ansible to use.

The next step is to use Ansible to install configuration files needed to connect to the internet through the Melbourne University proxy. This step is optional and can be skipped if the user finds a proxy unnecessary. Not all Nectar availability zones need the proxy, and setting it up when it is not needed can prevent network operations from working properly. Therefore, this is a separate step from the Ansible bootstrap script.

The Ansible bootstrap script is then used to install Docker on all the VMs. After that, a Docker context is set up, allowing the user to control the remote Docker swarm from their local machine. The Docker nodes are assigned labels so that we can constrain services, e.g. CouchDB, to run on specific nodes. To deploy the Docker stack, `node_up.py` uses `docker-compose` in the configured context to build the required containers for the remote Docker context, then pushes these containers to a registry set up on the VMs, before running `docker stack` to deploy services and other resources on that swarm. Frontend and Backend services are also deployed at this step.

The last step is to connect the deployed CouchDB instances into a single cluster. The script builds and runs the `couch_link` container, connected to the overlay network automatically created by the Docker stack containing our CouchDB nodes. This allows the script run by the `couch_link` container to locate and connect to the CouchDB instances and set up clustering between them.

### CouchDB Views
The views used to retrieve the AURIN data simply emit the stored data as no map-reduce processing is required. The view to retrieve the word length data is simple, and the map function used in the associated map-reduce is shown below. For each word in the Tweet, the map function simply emits the Tweet location and the word length as a key, and a 1 as the value (for summing purposes). The reduce function is the built-in `_sum` function.

```
function (doc) {
    doc.text.split(/\W+/).forEach(function (word) {
        if (["Adelaide", "Melbourne", "Hobart", "Darwin", "Sydney", 
        "Canberra", "Perth (WA)", "Brisbane"].includes(doc.place.name)) {
            emit([doc.place.name, word.length], 1);
        }
    });
}"
```

### Twitter Harvester
A prerequisite is that the user should have Python 3 installed in their machine.
To run the Twitter Harvester, the user first needs to install 2 python libraries:

```
pip install tweepy
pip install couchdb
```

Then, the harvest application can be started by running:

```python harvest.py```

Alternatively, the Twitter harvester can also be run as a Docker Container on our system.
### Backend Server
A prerequisite is that the user should have Python 3.9 installed in their machine.
To run the Backend server locally and separately, the user first needs to install all the requirements from requirements.txt

```pip install -r requirements.txt```

Then, the application is started on localhost:5000 by running:

```
COUCHDB_USER={couchdb-username} COUCHDB_PASSWORD={couchdb-password}\
COUCHDB_HOST={couchdb-ip-address}:{couchdb-port} python app.py
```

The endpoints supported include:

```
/chartdata?xattr={xattr}&yattr={yattr}
/api/graphkeys?attr={xattr}
/graphkeys?attr={yattr}
```

Details about each endpoint is elaborated in Section 3.5. Frontend.
### Frontend Application

Firstly, the `npm install` is run to install all required packages and dependencies.

```
npm install
```

Then `npm run build` will perform any necessary building and preparation tasks for the project.

```
npm run build
```

Lastly, `npm run dev` will compile all of the assets into a running application.

```
npm run dev
```
