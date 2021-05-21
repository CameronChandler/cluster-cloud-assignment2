import json
from getpass import getpass
from sys import argv
from os import environ, path
import os
from pprint import pprint
import subprocess
import argparse
import time
from dataclasses import dataclass
import hashlib
import uuid
import jinja2

from log import *

SCRIPT=path.realpath(__file__)
ROOT=path.dirname(SCRIPT)

PATHS = {
  'ansible': path.join(ROOT, 'cluster', 'ansible'),
  'heat': path.join(ROOT, 'cluster', 'heat'),
  'clouds': path.join(ROOT, 'clouds.yaml'),
  'stack': path.join(ROOT, 'containers'),
}


@contextmanager
def chdir(push):
  '''
  A context manager modelling changing into a directory, performing some operation,
  then returning to the original directory.
  '''
  stacked = os.getcwd()
  os.chdir(push)
  try: yield
  finally: os.chdir(stacked)

def gen_couchdb_password(password, salt=uuid.uuid4().hex, iterations=10):
  '''
  An (unused) function for generating CouchDB password fields using a consistent hash and iteration count.
  Would be useful for generating CouchDB config files with consistent hashed admin password, if that had
  been necessary to make clustering work properly.
  Unused for now, but included in case we need a reference implementation later on.
  '''
  hashed = hashlib.pbkdf2_hmac('sha1', password.encode(), salt.encode(), iterations, dklen=20)
  result = f'-pbkdf2-{hashed.hex()},{salt},{iterations}'
  return result

def gen_argparser():
  '''
  Generates the CLI argument parser used by `main`.
  '''
  parser = argparse.ArgumentParser()
  parser.add_argument('--os-cloud', default='nectar-private')
  parser.add_argument('--os-stack', default='stack')
  parser.add_argument('--os-keypair-name')
  parser.add_argument('--os-keypair-path', default='~/.ssh/id_rsa')

  parser.add_argument('--couch-user', default='admin')
  parser.add_argument('--couch-password', default='answering_railcar')
  parser.add_argument('--couch-secret', default='a192aeb9904e6590849337933b000c99')

  return parser

@dataclass
class CouchConfig:
  '''
  A data class used to model CouchDB configuration.
  '''
  username: str
  password: str
  secret: str

  def from_args(args):
    return CouchConfig(
      username=args.couch_user,
      password=args.couch_password,
      secret=args.couch_secret
    )

@dataclass
class OpenStackConfig:
  '''
  A data class used to model OpenStack configuration.
  '''
  cloud_name: str
  cloud_password: str
  stack_name: str
  stack_key_pair_name: str
  stack_key_pair_path: str

  def from_args(args):
    return OpenStackConfig(
      cloud_name=args.os_cloud,
      cloud_password=
        environ['OS_PASSWORD'] if 'OS_PASSWORD' in environ else getpass(f"Enter password for {args.os_cloud}: "),
      stack_name=args.os_stack,
      stack_key_pair_name=args.os_keypair_name,
      stack_key_pair_path=args.os_keypair_path,
    )

@dataclass
class DockerConfig:
  '''
  A data class used to model Docker configuration.
  '''
  context_name: str
  stack_name: str

  def from_os_config(os_config: OpenStackConfig):
    return DockerConfig(
      context_name=f'{os_config.cloud_name}_{os_config.stack_name}',
      stack_name='test'
    )

class Orchestrator:
  '''
  This is the main class used to interact with the configured machines.
  Includes functionality for orchestrating the OpenStack VMs, Docker Swarm, and the services that run on the swarm.
  '''
  def __init__(self, paths, os_config: OpenStackConfig, docker_config: DockerConfig, couch_config: CouchConfig):
    # Immutable stuff
    self.__paths = paths
    self.__os_config = os_config
    self.__docker_config = docker_config
    self.__couch_config = couch_config

    # Stateful stuff
    self.__known_stacks = None
    self.__stack_outputs = None

  def openstack_stack_exists(self, name):
    '''
    Checks whether an OpenStack "stack" with the name already exists by using the
    OpenStack CLI to fetch the list of deployed stacks.
    Will normally cache the list of stacks - this is invalidated e.g. in `openstack_create_or_update_stack`
    below to ensure following calls to `stack_exists` return a correct result.
    '''
    if not self.__known_stacks:
      trace('Fetching stack list')
      cmd = [
      'openstack',
      '--os-cloud', self.__os_config.cloud_name,
      'stack', 'list',
      '-f', 'json'
      ]
      proc = subprocess.Popen(
        cmd,
        env=environ.copy() | { 'OS_PASSWORD' : self.__os_config.cloud_password },
        stdout=subprocess.PIPE
      )
      stdout, _ = proc.communicate()
      stdout = stdout.decode()

      js = json.loads(stdout)
      self.__known_stacks = { s['Stack Name'] : s for s in js }
    return name in self.__known_stacks

  def openstack_create_or_update_stack(self):
    '''
    Creates or updates the OpenStack stack (set of VMs and other resources), using an
    OpenStack Heat template.
    '''
    action = 'create'
    if self.openstack_stack_exists(self.__os_config.stack_name):
      action = 'update'
      if input('Stack already exists, update it? (y/n): ') != 'y':
        return

    template = path.join(self.__paths['heat'], f'{self.__os_config.stack_name}.yaml')

    trace(f'{"updating" if action == "update" else "creating"} stack {self.__os_config.stack_name}')
    cmd = [
      'openstack',
      '--os-cloud', self.__os_config.cloud_name,
      'stack', action,
      '-f', 'json',
      '--wait',
      '-t', template,
      self.__os_config.stack_name,
      '--parameter', f'key_name={self.__os_config.stack_key_pair_name}'
    ]
    trace('Calling for effect: ' + ' '.join(cmd))
    result = subprocess.call(
      cmd,
      env=environ.copy() | { 'OS_PASSWORD' : self.__os_config.cloud_password },
    )

    assert(result == 0)
    
    self.__known_stacks = None
  
  @traced('Getting stack creation outputs')
  def openstack_get_stack_creation_outputs(self, name):
    '''
    OpenStack Heat supports stack creation "outputs", which can be retrieved to get information about the stack.
    In our case, we use this to get the IP addresses of the VMs created.
    '''
    with chdir(ROOT):
      if not self.__stack_outputs:
        cmd = [
          'pipenv',
          'run',
          'openstack',
          '--os-cloud', self.__os_config.cloud_name,
          'stack', 'output', 'show',
          '-f', 'json',
          '--all',
          name
        ]
        proc = subprocess.Popen(
          cmd,
          stdout=subprocess.PIPE,
          env=environ.copy() | { 'OS_PASSWORD' : self.__os_config.cloud_password }
        )

        stdout, _ = proc.communicate()
        stdout = stdout.decode()
        error(stdout)
        stdout = json.loads(stdout)
        for k in stdout:
          stdout[k] = json.loads(stdout[k])
        self.__stack_outputs = stdout
    
    return self.__stack_outputs
  
  @prompt('Generate hosts file')
  @traced()
  def write_hosts_file(self):
    '''
    Generate a hosts file for use by Ansible. This file has to be generated using the correct IP addresses,
    so we use the OpenStack stack creation outputs as described above.
    '''
    outputs = self.openstack_get_stack_creation_outputs(self.__os_config.stack_name)

    trace('Writing hosts file')
    with open(path.join(self.__paths['ansible'], 'generated_hosts.ini'), 'w') as hf:
      hf.write('[manager]\n')
      hf.write(f'{outputs["manager_ip"]["output_value"]} ansible_user=debian ansible_ssh_private_key_file={self.__os_config.stack_key_pair_path} ansible_python_interpreter=python3\n')
      hf.write('\n')
      hf.write('[worker]\n')
      for ip in outputs['worker_ips']['output_value'].split(','):
        hf.write(f'{ip} ansible_user=debian ansible_ssh_private_key_file={self.__os_config.stack_key_pair_path} ansible_python_interpreter=python3\n')
      hf.write('\n')

  @prompt('Set up unimelb proxy')
  @traced()
  def ansible_init_unimelb_proxy(self):
    '''
    Use Ansible to install configuration files needed to connect to the internet through the Melbourne Uni proxy server.
    This is a separate step from the Ansible bootstrap script because not all Nectar availability zones need the proxy,
    and setting it up when it's not needed can prevent network operations from working properly.
    If you don't need the proxy, you can safely skip this step.
    '''

    proc = subprocess.Popen([
      'ansible-playbook',
      # Ansible doesn't handle trying to do auth for multiple servers concurrently very well
      # See https://github.com/ansible/ansible/issues/25068
      '--forks', '1',  
      '-i', path.join(self.__paths['ansible'], 'generated_hosts.ini'),
      path.join(self.__paths['ansible'], 'unimelb-proxy.yml')
    ])
    proc.wait()

  @prompt('Run ansible')
  @traced()
  def ansible_bootstrap(self):
    '''
    Run the ansible bootstrap script to install Docker on all the VMs.
    '''
    manager = self.openstack_get_stack_creation_outputs(self.__os_config.stack_name)['manager_ip']['output_value']
    template_in = 'docker_daemon_config.json.jinja2'
    template_out = 'docker_daemon_config.json'
    proxy_config_dir = path.join(ROOT, 'cluster', 'ansible', 'roles', 'common', 'files')
    loader = jinja2.FileSystemLoader(searchpath=proxy_config_dir)
    env = jinja2.Environment(loader=loader)
    template = env.get_template(template_in)
    rendered = template.render({
      'registry_ip_port': ':'.join([manager, '4000'])
    })
    with open(path.join(proxy_config_dir, template_out), 'w') as f:
      f.write(rendered)


    proc = subprocess.Popen([
      'ansible-playbook',
      # Ansible doesn't handle trying to do auth for multiple servers concurrently very well
      # See https://github.com/ansible/ansible/issues/25068
      '--forks', '1',  
      '-i', path.join(self.__paths['ansible'], 'generated_hosts.ini'),
      path.join(self.__paths['ansible'], 'bootstrap.yml')
    ])
    proc.wait()
  
  # TODO(alaroldai): If docker context already exists, update it instead of deleting
  @prompt('Re-generate docker context')
  @traced('Creating docker context', 'docker')
  def docker_setup_remote_context(self):
    '''
    Set up a docker "context" allowing us to control the remote docker swarm from our local machine.
    Please note that Docker operations can be **extremely slow** when the context is unreachable
    (e.g. if the VM it was trying to connect to has been deallocated) - if that's the case, consider running
    `docker context use default` to switch back to a local context (although this will also be extremely slow)
    See https://github.com/docker/cli/issues/2584
    '''
    trace(f'Creating docker context {self.__docker_config.context_name}')
    outputs = self.openstack_get_stack_creation_outputs(self.__os_config.stack_name)
    manager = outputs['manager_ip']['output_value']
    exists = self.__docker_config.context_name in subprocess.check_output(['docker', 'context', 'ls', '-q']).decode().splitlines()
    action = 'update' if exists else 'create'
    subprocess.call([
      'docker', 'context', action,
      self.__docker_config.context_name,
      '--docker', f'host=ssh://debian@{manager}', '--description',
      'Generated by COMP90024 node-up.py script'
    ])
    subprocess.call(['docker', 'context', 'use', self.__docker_config.context_name])

    self.docker_label_nodes()
  
  @traced('Label docker nodes', 'docker')
  def docker_label_nodes(self):
    '''
    Assign labels to the docker nodes so that we can constrain services (e.g. CouchDB) to run on specific nodes
    '''
    nodes = [s.strip() for s in subprocess.check_output(['docker', 'node', 'ls', '-q']).decode().splitlines()]
    for i, n in enumerate(nodes):
      cmd = ['docker', 'node', 'update', '--label-add', f'index={i}', n]
      trace('Calling for effect: ' + ' '.join(cmd))
      subprocess.call(cmd)

  @traced()
  def start_docker_registry_service(self):
    outputs = self.openstack_get_stack_creation_outputs(self.__os_config.stack_name)
    hostname = outputs['manager_ip']['output_value']
    cmd = ['docker', 'service', 'create', '--name', 'registry', '-p', '4000:5000', 'registry:2']
    subprocess.call(cmd)
    self.__docker_registry_address_port = ':'.join([hostname, '4000'])

  @traced('Generating docker-compose.yaml')
  def docker_gen_compose_definition(self):
    '''
    Generate a `docker-compose.yaml` file from the Jinja2 template.
    This is used to ensure the correct CouchDB username and password are used, and
    because the resulting docker-compose.yaml file is in the `.gitignore`, also prevents the couchdb credentials
    from being accidentally committed and publically shared.
    '''
    loader = jinja2.FileSystemLoader(searchpath='./')
    env = jinja2.Environment(loader=loader)
    template = env.get_template('docker-compose-template.yaml')
    compose = template.render({
      'couchdb_username' : self.__couch_config.username,
      'couchdb_password' : self.__couch_config.password,
      'couchdb_secret' : self.__couch_config.secret,
      'registry_address_port': self.__docker_registry_address_port,
    })
    with open('docker-compose.yaml', 'w') as f:
      f.write(compose)

  @prompt('Deploy docker stack')
  @traced('Deploying docker stack', 'docker')
  def docker_deploy_stack(self):
    '''
    Please note that a Docker "stack" is different from an OpenStack "stack".
    A Docker stack refers to a set of services and other resources deployed on a docker swarm.
    This function uses docker-compose in the configured context to build the required containers for the remote
    docker context, then uses `docker stack` to deploy services and other resources onto that swarm.
    '''
    with chdir(self.__paths['stack']):
      subprocess.call(['docker', 'stack', 'rm', self.__docker_config.stack_name])

      self.start_docker_registry_service()

      self.docker_gen_compose_definition()

      subprocess.call(['docker-compose', 'build'])
      subprocess.call(['docker-compose', 'push'])
      subprocess.call([
        'docker',
        'stack',
        'deploy',
        '-c', 'docker-compose.yaml',
        self.__docker_config.stack_name,
      ])
    info('Sleeping 30s to give couch containers time to start')
    time.sleep(30)
    info('The amount of time taken for all containers to start seems to have a lot of variance - consider running `docker ps -a` to check that all containers have been deployed before continuing.')
  
  @prompt('Link CouchDB cluster')
  @traced('linking couchdb cluster', 'docker')
  def link_couch(self):
    '''
    Builds and runs the "couch_link" container, connected to the overlay network automatically created
    by the docker stack containing our couchdb nodes.
    This allows the script run by the couch_link container to locate and connect to the CouchDB instances and
    set up clustering between those instances.
    '''
    with chdir(self.__paths['stack']):
      subprocess.call([
        'docker',
        'build',
        '--build-arg',
        'http_proxy=http://wwwproxy.unimelb.edu.au:8000',
        '-t',
        'comp90024/couch_link',
        'couch-link'
      ])
      subprocess.call([
        'docker',
        'run',
        '--network', '_'.join([self.__docker_config.stack_name, 'couch']),
        '--env', f'COUCH_USER={self.__couch_config.username}',
        '--env', f'COUCH_PASSWORD={self.__couch_config.password}',
        'comp90024/couch_link'
      ])

  # @prompt('Deploy CouchDB Views')
  # @traced('Deploying CouchDB Views')
  # def deploy_views(self):
  #   '''
  #   Finish configuring the CouchDB cluster by installing design docs
  #   '''
  #   for view in os.listdir('couchdb/views'):
  #     with open(view, 'r') as f:
  #       viewstring = f.read()
  #       subprocess.call([
  #         'curl',
  #         '-X', 'PUT',
  #         f'http://admin:password@{}:5984/db/_design/my_ddoc',
  #         '-d ', viewstring
  #       ])

def main():
  parser = gen_argparser()
  args = parser.parse_args()

  os_config = OpenStackConfig.from_args(args)
  client = Orchestrator(
    paths=PATHS,
    os_config=os_config,
    docker_config=DockerConfig.from_os_config(os_config),
    couch_config=CouchConfig.from_args(args)
  )

  client.openstack_create_or_update_stack()
  client.write_hosts_file()
  client.ansible_init_unimelb_proxy()
  client.ansible_bootstrap()
  client.docker_setup_remote_context()
  client.docker_deploy_stack()
  client.link_couch()
  # client.deploy_views()

if __name__ == '__main__':
  main()
