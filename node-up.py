import asyncio
import json
from getpass import getpass
from sys import argv
from os import environ, path
import os
from pprint import pprint
import subprocess
import argparse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from functools import lru_cache

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

from log import *

class OpenStackClient:
  def __init__(self, cloud_name, stack_name):
    self.__cloud_name = cloud_name
    self.__stack_name = stack_name
    self.__password = None
    self.__known_stacks = None
    self.__stack_outputs = None
    self.__docker_context_name = None
    self.__jinja2_env = Environment(
      loader=FileSystemLoader(ROOT),
      autoescape=select_autoescape(['yaml', 'html', 'xml'])
    )
  
  @lru_cache
  def load_template(self, path):
    return self.__jinja2_env.get_template(path)
  
  def render_template(self, path, **kwargs):
    return self.load_template(path).render(**kwargs)

  @property
  def password(self):
    if not self.__password:
      self.__password = environ['OS_PASSWORD'] if 'OS_PASSWORD' in environ else None
    if not self.__password:
      self.__password = getpass(f"Enter password for {self.__cloud_name}: ")
    return self.__password    

  async def stack_exists(self, name):
    if not self.__known_stacks:
      trace('Fetching stack list')
      cmd = [
      'openstack',
      '--os-cloud', self.__cloud_name,
      'stack', 'list',
      '-f', 'json'
      ]
      proc = await asyncio.create_subprocess_exec(
        *cmd,
        env=environ.copy() | { 'OS_PASSWORD' : self.password },
        stdout=asyncio.subprocess.PIPE
      )
      stdout, _ = await proc.communicate()
      stdout = stdout.decode()

      js = json.loads(stdout)
      self.__known_stacks = { s['Stack Name'] : s for s in js }
    pprint(self.__known_stacks)
    return name in self.__known_stacks

  async def create_stack(self, template, params):
    action = 'create'
    if await self.stack_exists(self.__stack_name):
      action = 'update'
      if input('Stack already exists, update it? (y/n): ') != 'y':
        return
    trace(f'{"updating" if action == "update" else "creating"} stack {self.__stack_name}')
    cmd = [
      'openstack',
      '--os-cloud', self.__cloud_name,
      'stack', action,
      '-f', 'json',
      '--wait',
      '-t', template,
      self.__stack_name
    ] + [i for key, value in params.items() for i in ['--parameter', f'{key}={value}']]
    trace('Calling for effect: ' + ' '.join(cmd))
    proc = await asyncio.create_subprocess_exec(
      *cmd,
      env=environ.copy() | { 'OS_PASSWORD' : self.password },
      stdout=asyncio.subprocess.PIPE
    )

    assert(await proc.wait() == 0)
  
  @traced('Getting stack creation outputs')
  async def get_outputs(self, name):
    if not self.__stack_outputs:
      cmd = [
        'openstack',
        '--os-cloud', self.__cloud_name,
        'stack', 'output', 'show',
        '-f', 'json',
        '--all',
        name
      ]
      proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        env=environ.copy() | { 'OS_PASSWORD' : self.password }
      )

      stdout, _ = await proc.communicate()
      stdout = stdout.decode()
      stdout = json.loads(stdout)
      for k in stdout:
        stdout[k] = json.loads(stdout[k])
      self.__stack_outputs = stdout

    pprint(self.__stack_outputs)
    
    return self.__stack_outputs
  
  @prompt('Generate hosts file')
  @traced()
  async def write_hosts_file(self):
    outputs = await self.get_outputs(self.__stack_name)

    pprint(self.__stack_outputs)
    outputs = self.__stack_outputs
    pprint(outputs)

    trace('Writing hosts file')
    with open(path.join(PATHS['ansible'], 'generated_hosts.ini'), 'w') as hf:
      hf.write('[manager]\n')
      hf.write(f'{outputs["manager_ip"]["output_value"]} ansible_user=debian ansible_ssh_private_key_file=~/.ssh/id_rsa ansible_python_interpreter=python3\n')
      hf.write('\n')
      hf.write('[worker]\n')
      hf.write(f'{outputs["worker_ip"]["output_value"]} ansible_user=debian ansible_ssh_private_key_file=~/.ssh/id_rsa ansible_python_interpreter=python3\n')
      hf.write('\n')

  @prompt('Run ansible')
  @traced()
  async def run_ansible(self):
    proc = subprocess.Popen([
      'ansible-playbook',
      # Ansible doesn't handle trying to do auth for multiple servers concurrently very well
      # See https://github.com/ansible/ansible/issues/25068
      '--forks', '1',  
      '-i', path.join(PATHS['ansible'], 'generated_hosts.ini'),
      path.join(PATHS['ansible'], 'bootstrap.yml')
    ])
    proc.wait()
  
  @property
  def docker_context_name(self):
    return self.__cloud_name + '_' + self.__stack_name
  
  # TODO(alaroldai): If docker context already exists, update it instead of deleting
  @prompt('Re-generate docker context')
  @traced('Creating docker context', 'docker')
  async def setup_docker_context(self):
    trace(f'Creating docker context {self.docker_context_name}')
    outputs = await self.get_outputs(self.__stack_name)
    manager = outputs['manager_ip']['output_value']
    subprocess.call([
      'docker', 'context', 'create',
      self.docker_context_name,
      '--docker', f'host=ssh://debian@{manager}', '--description',
      'Generated by COMP90024 node-up.py script'
    ])
    subprocess.call(['docker', 'context', 'use', self.docker_context_name])
  
  @prompt('Deploy docker registry service')
  @traced('Deploying docker registry service', 'docker')
  async def deploy_registry(self):
    subprocess.call(['docker', 'service', 'create', '--name', 'registry', '-p', '5000:5000', 'registry:2'])

  @prompt('Deploy docker stack')
  @traced('Deploying docker stack', 'docker')
  async def deploy_docker_stack(self):
    # Build required containers
    await asyncio.gather(
      (
        await asyncio.create_subprocess_exec(
          'docker', 'build', '-t', 'comp90024/' + p, PATHS[p]
        )
      ).wait()
      for p in ('couch', 'nginx')
    )
      
    # Load the stack template
    # compose = self.render_template(path.join(PATHS['couch'], 'docker-compose.yaml'))

    # Deploy the stack
    proc = subprocess.Popen(
      [
        'docker', 'stack', 'deploy', '-c', path.join(PATHS['stack'], 'docker-compose.yaml'), self.__stack_name
      ],
    )
    proc.wait()
  
  async def cleanup_container_by_name(self, name):
    stdout, _ = await (
        await asyncio.create_subprocess_exec(
          'docker', 'ps', '--all', '--filter', f'name={name}', '--quiet',
          stdout=asyncio.subprocess.PIPE
        )
      ).communicate()
    stdout = stdout.decode()

    if stdout:
      await (
        await asyncio.create_subprocess_exec(
          'docker', 'stop', name
        )
      ).wait()
      await (
        await asyncio.create_subprocess_exec(
          'docker', 'rm', name
        )
      ).wait()

  async def build_couch_container(self):
    await (
      await asyncio.create_subprocess_exec('docker', 'build', '-t', 'comp90024/couch_wrapper', PATHS['couch'])
    ).wait()
  
  def couchdb_container_name(self, address):
    return f'couchdb{address}'

  async def deploy_couch(self, address, user, password, cookie):
    print(f'deploying {self.couchdb_container_name(address)}')
    await (
      await asyncio.create_subprocess_exec(
        'docker', 'create',
        '--name', self.couchdb_container_name(address),
        '--env',  f'COUCHDB_USER={user}',
        '--env',  f'COUCHDB_PASSWORD={password}',
        '--env',  f'COUCHDB_SECRET={cookie}',
        '--env',  f'ERL_FLAGS=-setcookie "{cookie}" -name "couchdb@{address}" -kernel inet_dist_listen_min 9100 -kernel inet_dist_listen_max 9200',
        'comp90024/couch_wrapper:latest'
      )
    ).wait()
    await (
      await asyncio.create_subprocess_exec(
        'docker', 'start', self.couchdb_container_name(address)
      )
    ).wait()
  
  async def connect_couch_cluster(self):
    proc = subprocess.Popen([
      'ansible-playbook',
      '--forks', '1',  
      '-i', path.join(PATHS['ansible'], 'generated_hosts.ini'),
      path.join(PATHS['ansible'], 'couch-up.yml')
    ])
    proc.wait()

  @prompt('Deploy couch (without service)')
  @traced('Deploying couch')
  async def deploy_couch_no_service(self):
    # Assumes that we're already using the cluster's docker context
    nodes = ('172.17.0.4', '172.17.0.3', '172.17.0.2')
    # Stop any running containers
    await asyncio.gather(*[
      self.cleanup_container_by_name(self.couchdb_container_name(node)) for node in nodes
    ])
    await self.build_couch_container()
    for node in sorted(nodes):
      await self.deploy_couch(node, 'admin', 'answering_railcar', 'a192aeb9904e6590849337933b000c99')
  
    # Connecting the couch cluster together requires access to its network,
    # so we use ansible to run a shell script on the main node
    await self.connect_couch_cluster()

  @prompt('Deploy nginx (without service)')
  @traced('Deploying nginx')
  async def deploy_nginx_no_service(self):
    if not await (
        await asyncio.create_subprocess_exec(
          'docker', 'build', '-t', 'comp90024/nginx', PATHS['nginx']
        )
      ).wait():
      warning('Failed to build nginx image')

    await self.cleanup_container_by_name('nginx')

    if not await (
        await asyncio.create_subprocess_exec(
          'docker', 'create', '--name', 'nginx', '-p', '6984:6984', 'comp90024/nginx:latest',
        )
      ).wait():
      warning('Failed to create nginx container')

    if not await (
        await asyncio.create_subprocess_exec(
          'docker', 'start', 'nginx',
        )
      ).wait():
      fatal('Failed to start nginx')

async def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--cloud', default='nectar-private')
  parser.add_argument('--stack', default='test')
  args = parser.parse_args()

  client = OpenStackClient(args.cloud, args.stack)
  await client.create_stack(path.join(PATHS['heat'], 'stack.yaml'), {'key_name': 'alaroldai_haliax'})
  await client.write_hosts_file()
  await client.run_ansible()
  await client.setup_docker_context()
  await client.deploy_couch_no_service()
  await client.deploy_nginx_no_service()


if __name__ == '__main__':
  asyncio.run(main())
