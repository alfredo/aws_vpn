import ConfigParser
import time
import os

from boto import ec2

from fabric.api import run, local, env, get, sudo, cd
from fabric.colors import yellow, red
from fabric.contrib import console


PROJECT_ROOT = os.path.dirname(os.path.realpath(__file__))
here = lambda *x: os.path.join(PROJECT_ROOT, *x)

config = ConfigParser.ConfigParser()
config.readfp(open(here('settings.cfg')))

# Configuration for the instance
EC2_INSTANCE_TYPE = 't1.micro'
AMI_ID = 'ami-9c78c0f5'
key = config.get('aws', 'key')
secret = config.get('aws', 'secret')
conn = ec2.EC2Connection(key, secret)

SECURITY_GROUP = 'proxy-aws-sg'

KEY_PAIR = config.get('aws', 'key_pair')
KEY_PATH = os.path.expanduser('~/.ssh/%s.pem' % KEY_PAIR)

USER = config.get('vpn', 'user')
PASSWORD = config.get('vpn', 'password')

# Tag name.
TAG_NAME = 'proxy-aws'


def _get_instance_details(instance):
    return {
        'id': instance.id,
        'url': instance.public_dns_name,
        'state': instance.state,
        'name': instance.tags.get('Name'),
    }


def ls():
    for reservation in conn.get_all_instances():
        for i in reservation.instances:
            print _get_instance_details(i)


def _create_proxy_group():
    print yellow('Security group not existing, creating one.')
    group = conn.create_security_group(SECURITY_GROUP,
                                       'AWS VPN security group.')
    group.authorize(ip_protocol='tcp', from_port=0, to_port=65535,
                    cidr_ip='0.0.0.0/0')
    group.authorize(ip_protocol='udp', from_port=0, to_port=65535,
                    cidr_ip='0.0.0.0/0')
    return group.name


def _get_proxy_group():
    print yellow('Retrieving security group.')
    groups = conn.get_all_security_groups()
    for group in groups:
        if group.name == SECURITY_GROUP:
            return group.name
    return _create_proxy_group()


def _get_proxy_instance(tag_name):
    """Returns the ID of the provisioned machine if any.
    We assume the machine is provisioned if it matches our ``TAG_NAME``"""
    for reservation in conn.get_all_instances():
        for i in reservation.instances:
            # Ignore ``terminated`` instances.
            if i.state in ['terminated', 'shutting-down']:
                continue
            if i.tags.get('Name') == tag_name:
                if i.state in ['pending']:
                    print red('FAILURE: Instance is starting up.')
                    return exit(1)
                return _get_instance_details(i)
    # There is no instance with our tag, we assume it hasn't been created
    return {}


def _start_instance():
    """Starts an instance and tags it with the ``TAG_NAME``"""
    print yellow('Provisioning instance.')
    reservations = conn.run_instances(
        AMI_ID,
        key_name=KEY_PAIR,
        instance_type=EC2_INSTANCE_TYPE,
        security_groups=[_get_proxy_group()]
    )
    instance = reservations.instances[0]
    status = instance.update()
    while status == 'pending':
        time.sleep(5)
        status = instance.update()
        print yellow('Not provisioned, yet.')
    if status == 'running':
        print yellow('Instance %s has been provisioned.' % instance.id)
        instance.add_tag("Name", TAG_NAME)
        # Give it a bit of time so we make sure we can actually use it.
        time.sleep(30)
    else:
        message = "FAILURE: Instance status %s." % status
        print red(message)
        return exit(1)
    return _get_instance_details(instance)


def _set_instance_connection(instance):
    """Prepares the connection."""
    print yellow('Preparing connection.')
    env.user = 'ubuntu'
    env.host_string = instance['url']
    env.connection_attempts = 10
    env.key_filename = KEY_PATH
    return True


def _provision_instance(instance):
    """Installs and configure any required package"""
    _set_instance_connection(instance)
    print yellow('Installing  and configuring required packages.')
    sudo('apt-get -q -y install pptpd')
    run('echo "localip 192.168.240.1\nremoteip 192.168.240.2-9" | '
        'sudo tee -a /etc/pptpd.conf')
    run('echo "ms-dns 8.8.8.8\nms-dns 8.8.4.4" | '
        'sudo tee -a /etc/ppp/pptpd-options')
    run('echo "%s pptpd %s *" | sudo tee -a /etc/ppp/chap-secrets'
        % (USER, PASSWORD))
    sudo("sed -i 's/\#net\.ipv4\.ip_forward\=1/net\.ipv4\.ip_forward\=1/g'"
         " /etc/sysctl.conf")
    sudo('sysctl -p')
    iptables_cmd = 'iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE'
    sudo(iptables_cmd)
    sudo("sed -i 's/^exit 0/%s\\n&/g' /etc/rc.local" % iptables_cmd)
    sudo('/etc/init.d/pptpd restart')
    print yellow('Installation completed.')
    sudo("reboot")
    print yellow('Intance available at:')
    print yellow(instance['url'])


def _stop_instance(instance_id):
    return conn.stop_instances(instance_ids=[instance_id])


def provision():
    """Provisions the EC2 instance."""
    confirmation = red('You are about to Provision an EC2 %s instance.'
                       ' Procceed? ' % EC2_INSTANCE_TYPE)
    if console.confirm(confirmation):
        instance = _get_proxy_instance(TAG_NAME)
        if instance:
            message = 'FAILURE: Instance has been already provisioned'
            print red(message)
            return exit(1)
        # Instance does not exist, create it.
        instance = _start_instance()
        _provision_instance(instance)
        return instance
    else:
        print yellow('Phew, aborted.')


def halt():
    """Halts the EC2 instance."""
    instance = _get_proxy_instance(TAG_NAME)
    if instance and instance['state'] in ['running']:
        print yellow('Stopping instance.')
        local('osascript %s/vpnconnection.scpt %s halted'
              '' % (PROJECT_ROOT, TAG_NAME))
        conn.stop_instances([instance['id']])
        return exit(0)
    print red('FAILURE: Instance cannot be stopped.')
    print instance
    return exit(1)


def up():
    """Starts the EC2 instance."""
    instance = _get_proxy_instance(TAG_NAME)
    # Make sure the instance exists and has one of our valid status.
    if instance and instance['state'] in ['stopped', 'running']:
        print yellow('Starting instance.')
        if instance['state'] == 'stopped':
            conn.start_instances([instance['id']])
            # Give it sometime to load
            time.sleep(30)
        print yellow(instance['url'])
        local('osascript %s/vpnconnection.scpt %s %s'
              '' % (PROJECT_ROOT, TAG_NAME, instance['url']))
        return exit(0)
    print red('FAILURE: Instance cannot be started.')
    print instance
    return exit(1)
