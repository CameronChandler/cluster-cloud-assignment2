import asyncio
import json
from getpass import getpass
from sys import argv
from os import environ
from pprint import pprint
import subprocess


from log import *

class OpenStackClient:
  def __init__(self, cloud_name):
    self.__cloud_name = cloud_name
    self.__password = None
    self.__known_stacks = None

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

  async def create_stack(self, template, name, params):
    action = 'create'
    if await self.stack_exists(name):
      action = 'update'
      if input('Stack already exists, update it? (y/n): ') != 'y':
        return
    trace(f'{"updating" if action == "update" else "creating"} stack {name}')
    cmd = [
      'openstack',
      '--os-cloud', self.__cloud_name,
      'stack', action,
      '-f', 'json',
      '--wait',
      '-t', template,
      name
    ] + [i for key, value in params.items() for i in ['--parameter', f'{key}={value}']]
    trace('Calling for effect: ' + ' '.join(cmd))
    proc = await asyncio.create_subprocess_exec(
      *cmd,
      env=environ.copy() | { 'OS_PASSWORD' : self.password },
      stdout=asyncio.subprocess.PIPE
    )

    assert(await proc.wait() == 0)
  
  async def get_outputs(self, name):
    trace('Getting stack creation outputs')
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
    
    return stdout
  
  async def write_hosts_file(self, stack_name):
    outputs = await self.get_outputs(stack_name)
    trace('Writing hosts file')
    with open('ansible/generated_hosts.ini', 'w') as hf:
      hf.write('[manager]\n')
      hf.write(f'{outputs["manager_ip"]["output_value"]} ansible_user=debian ansible_ssh_private_key_file=~/.ssh/id_rsa ansible_python_interpreter=python3\n')
      hf.write('\n')
      hf.write('[worker]\n')
      hf.write(f'{outputs["worker_ip"]["output_value"]} ansible_user=debian ansible_ssh_private_key_file=~/.ssh/id_rsa ansible_python_interpreter=python3\n')
      hf.write('\n')

  def run_ansible(self):
    trace('Running ansible')
    proc = subprocess.Popen([
      'ansible-playbook',
      # Ansible doesn't handle trying to do auth for multiple servers concurrently very well
      # See https://github.com/ansible/ansible/issues/25068
      '--forks', '1',  
      '-i', 'ansible/generated_hosts.ini',
      'ansible/bootstrap.yml'
    ])
    proc.wait()

async def main():
  client = OpenStackClient('nectar-private')
  await client.create_stack('heat/stack.yaml', 'test', {'key_name': 'alaroldai_haliax'})
  if input('Continue? ') != 'y':
    return
  await client.write_hosts_file('test')
  await client.run_ansible()

if __name__ == '__main__':
  asyncio.run(main())
