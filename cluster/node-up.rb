require 'shellwords'

# Assuming we're working with a fresh vm...

class ComputeInstanceBuilder
  attr_reader :username

  def initialize(cloud_name, image_id, flavor_id, ssh_key, security_groups, username)
    @cloud_name = Shellwords.escape(cloud_name)
    @image_id = Shellwords.escape(image_id)
    @flavor_id = Shellwords.escape(flavor_id)
    @ssh_key = Shellwords.escape(ssh_key)
    @security_groups = security_groups.map { |key| Shellwords.escape(key) }
    @username = username
  end

  def build(name)

    security_groups = @security_groups
      .map { |group| "--security-group #{group}" }
      .join(' ')
    
    puts "creating #{name}"
    `openstack --os-cloud #{@cloud_name} server create \
      --wait \
      --image #{@image_id} \
      --flavor #{@flavor_id} \
      --key-name #{@ssh_key} \
      #{security_groups} \
      #{name}
    `

    return ComputeInstance.new(self, name)
  end

end
# ansible_user=debian ansible_ssh_private_key_file=~/.ssh/id_rsa ansible_python_interpreter=python3
class ComputeInstance
  attr_reader :name
  attr_reader :builder
  attr_accessor :ip

  def initialize(builder, name)
    @builder = builder
    @name = name
  end

  def append_to_hostfile(writer, keyfile)
    writer.puts("#{@ip} ansible_user=#{@builder.username} ansible_ssh_private_key_file=#{keyfile} ansible_python_interpreter=python3")
  end

  def self.write_hostfile(instances, keyname, path)
    puts "Path to private key for keypair #{keyname}: "
    keypath = gets.strip
    open(path, 'w') { |f|
      f.puts('[manager]')
      instances[0].append_to_hostfile(f, keypath)
      f.puts('[worker]')
      instances[1..].each { |i| i.append_to_hostfile(f, keypath) }
    }
  end

  def self.populate_ips(instances, cloud_name)
    # Get server info from openstack
    host_names = instances.map { |i| "--host #{Shellwords.escape(i.name)}" }.join(' ')
    # Columns are <empty>, id, name, status, networks, image, flavor
    ips = `openstack --os-cloud #{cloud_name} server list #{host_names}`
      .lines
      .filter_map { |l|
        cols = l.split('|')
        [cols[2].strip, cols[4].strip] if cols.length > 4
      }
    puts ips.inspect
    ips = ips
      .filter_map { |l|
        networks_split = l[1].strip.split('=')
        if networks_split.length < 2 then
          nil
        else
          l[1] = networks_split[1]
          l
        end
      }
      .to_h
    puts ips.inspect
    instances.each { |i|
      puts "Found ip: #{i.name} -> #{ips[i.name]}"
      i.ip = ips[i.name]
    }
  end

  def self.ansible_up(instances, hostfile)
    system("ansible-playbook -i #{hostfile} ansible/bootstrap.yml")
  end
end

builder = ComputeInstanceBuilder.new(
  'nectar-private',
  'NeCTAR Debian 10 (Buster) amd64',
  't3.xsmall',
  'alaroldai_haliax',
  ['default', 'ssh', 'mosh', 'icmp'],
  'debian'
)

# instances = ['test', 'test2']
#   .map { |name| builder.build(name) } # -> [ComputeInstance]
instances = [
  ComputeInstance.new(builder, 'test'),
  ComputeInstance.new(builder, 'test2'),
]
ComputeInstance.populate_ips(instances, 'nectar-private')
ComputeInstance.write_hostfile(instances, 'alaroldai_haliax', 'ansible/generated_hosts.ini')
ComputeInstance.ansible_up(instances, 'ansible/generated_hosts.ini')
