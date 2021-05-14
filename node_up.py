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
  'stack': path.join(ROOT, 'docker', 'stack'),
  'couch': path.join(ROOT, 'docker', 'stack', 'couch'),
  'nginx': path.join(ROOT, 'docker', 'stack', 'nginx')
}

@contextmanager
def chdir(push):
  stacked = os.getcwd()
  os.chdir(push)
  # try: yield
  # finally: os.chdir(stacked)
  yield
  os.chdir(stacked)

def gen_couchdb_password(password, salt=uuid.uuid4().hex, iterations=10):
  hashed = hashlib.pbkdf2_hmac('sha1', password.encode(), salt.encode(), iterations, dklen=20)
  result = f'-pbkdf2-{hashed.hex()},{salt},{iterations}'
  return result

def gen_argparser():
  parser = argparse.ArgumentParser()
  parser.add_argument('--os-cloud', default='nectar-private')
  parser.add_argument('--os-stack', default='test')
  parser.add_argument('--os-keypair-name')
  parser.add_argument('--os-keypair-path', default='~/.ssh/id_rsa')

  parser.add_argument('--couch-user', default='admin')
  parser.add_argument('--couch-password', default='answering_railcar')
  parser.add_argument('--couch-secret', default='a192aeb9904e6590849337933b000c99')

  return parser

@dataclass
class CouchConfig:
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
  context_name: str

  def from_os_config(os_config: OpenStackConfig):
    return DockerConfig(
      context_name=f'{os_config.cloud_name}_{os_config.stack_name}'
    )

class OpenStackClient:
  def __init__(self, paths, os_config: OpenStackConfig, docker_config: DockerConfig, couch_config: CouchConfig):
    # Immutable stuff
    self.__paths = paths
    self.__os_config = os_config
    self.__docker_config = docker_config
    self.__couch_config = couch_config

    # Stateful stuff
    self.__known_stacks = None
    self.__stack_outputs = None

  def stack_exists(self, name):
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

  def create_stack(self):
    action = 'create'
    if self.stack_exists(self.__os_config.stack_name):
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
  
  @traced('Getting stack creation outputs')
  def get_outputs(self, name):
    if not self.__stack_outputs:
      cmd = [
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
      stdout = json.loads(stdout)
      for k in stdout:
        stdout[k] = json.loads(stdout[k])
      self.__stack_outputs = stdout
    
    return self.__stack_outputs
  
  @prompt('Generate hosts file')
  @traced()
  def write_hosts_file(self):
    outputs = self.get_outputs(self.__os_config.stack_name)

    outputs = self.__stack_outputs

    trace('Writing hosts file')
    with open(path.join(self.__paths['ansible'], 'generated_hosts.ini'), 'w') as hf:
      hf.write('[manager]\n')
      hf.write(f'{outputs["manager_ip"]["output_value"]} ansible_user=debian ansible_ssh_private_key_file={self.__os_config.stack_key_pair_path} ansible_python_interpreter=python3\n')
      hf.write('\n')
      hf.write('[worker]\n')
      hf.write(f'{outputs["worker_ip"]["output_value"]} ansible_user=debian ansible_ssh_private_key_file={self.__os_config.stack_key_pair_path} ansible_python_interpreter=python3\n')
      hf.write('\n')

  @prompt('Set up unimelb proxy')
  @traced()
  def init_unimelb_proxy(self):
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
  def run_ansible(self):
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
  def setup_docker_context(self):
    trace(f'Creating docker context {self.__docker_config.context_name}')
    outputs = self.get_outputs(self.__os_config.stack_name)
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

  @traced('Generating docker-compose.yaml')
  def gen_compose_definition(self):
      loader = jinja2.FileSystemLoader(searchpath='./')
      env = jinja2.Environment(loader=loader)
      template = env.get_template('docker-compose-template.yaml')
      compose = template.render({
        'couchdb_username' : self.__couch_config.username,
        'couchdb_password' : self.__couch_config.password,
        'couchdb_secret' : self.__couch_config.secret,
      })
      with open('docker-compose.yaml', 'w') as f:
        f.write(compose)

  @prompt('Deploy docker stack')
  @traced('Deploying docker stack', 'docker')
  def deploy_docker_stack(self):
    with chdir(self.__paths['stack']):
      self.gen_compose_definition()

      subprocess.call(['docker-compose', 'build'])
      subprocess.call([
        'docker',
        'stack',
        'deploy',
        '-c', 'docker-compose.yaml',
        'test',
      ])
    info('Sleeping 15s to give couch containers time to start')
    time.sleep(15)
  
  @prompt('Link CouchDB cluster')
  @traced('linking couchdb cluster', 'docker')
  def link_couch(self):
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
        '--network', 'test_couch',
        '--env', f'COUCH_USER={self.__couch_config.username}',
        '--env', f'COUCH_PASSWORD={self.__couch_config.password}',
        'comp90024/couch_link'
      ])

    @prompt('Deploy CouchDB Views')
    @traced('Deploying CouchDB Views')
    def deploy_views(self):
      for view in os.listdir('couchdb/views'):
        with open(view, 'r') as f:
          viewstring = f.read()
          subprocess.call([
            'curl',
            '-X', 'PUT',
            f'http://admin:password@{}:5984/db/_design/my_ddoc',
            '-d ', viewstring
          ])

def main():
  parser = gen_argparser()
  args = parser.parse_args()

  os_config = OpenStackConfig.from_args(args)
  client = OpenStackClient(
    paths=PATHS,
    os_config=os_config,
    docker_config=DockerConfig.from_os_config(os_config),
    couch_config=CouchConfig.from_args(args)
  )

  client.create_stack()
  client.write_hosts_file()
  client.init_unimelb_proxy()
  client.run_ansible()
  client.setup_docker_context()
  client.deploy_docker_stack()
  client.link_couch()
  client.deploy_views()

if __name__ == '__main__':
  main()
