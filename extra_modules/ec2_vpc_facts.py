#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Author: Dave Hirko @DaveHirko
# Documentation section
DOCUMENTATION = '''
---
version_added: "3.0"
module: ec2_vpc_facts
author: Dave Hirko (@davehirko)
short_description: Returns information about a VPC
description:
  - This module returns information about a VPC and can be queried in two ways
options:
  vpc_id:
    description:
      - The VPC identifier for the queried VPC
    required: no
  region:
    description:
      The AWS Region of the VPC
    required: yes
  name:
    description:
      The Name tag of the VPC
    required: no
  cidr:
    description:
      The CIDR Block of the VPC
    required: no
  aws_access_key:
    description:
      Public access key
    required: yes
  aws_secret_key:
    description:
      Secret access key
    required: yes
'''

EXAMPLES = '''
- name: Get VPC Information
  ec2_vpc_facts:
    vpc_id: vpc-abcd12ef
    region: us-east-1
    aws_access_key: IDSFSFSDFN
    aws_secret_key: sncosncioconcois

- name: Get VPC Information
  ec2_vpc_facts:
    name: customer_vpc
    cidr: 10.0.1.0/16
    region: us-east-1
    aws_access_key: IDSFSFSDFN
    aws_secret_key: sncosncioconcois
'''

try:
    import boto
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False


# Logic of the module
def get_vpc_response(module, client, name, cidr_block, vpc_id):

    if (name and cidr_block) or vpc_id:
        if vpc_id:
            id_filter = [{'Name': 'vpc-id', 'Values': [vpc_id]}]
            vpc_response = client.describe_vpcs(Filters=id_filter)
        elif (name and cidr_block):
            name_filter = [{'Name': 'tag:Name', "Values": [name]}, {'Name': 'cidr', 'Values': [cidr_block]}]
            vpc_response = client.describe_vpcs(Filters=name_filter)
        else:
            module.fail_json(msg="Something went wrong filtering for correct module parameters")
    else:
        module.fail_json(msg="The wrong combination of parameters was supplied. See documentation.")

    return vpc_response


def get_ec2_boto3_client(module, region, aws_access_key, aws_secret_key):
    try:
        ec2 = boto3.client('ec2', region_name=region, aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key)
    except Exception, e:
        module.fail_json(msg="Could not return an EC2 client resource " + str(e))
    return ec2


def get_asg_boto3_client(module, region, aws_access_key, aws_secret_key):
    try:
        asg = boto3.client('autoscaling', region_name=region, aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key)
    except Exception, e:
        module.fail_json(msg="Could not return an autoscale client resource " + str(e))
    return asg


def get_ec2_resource(module, region, aws_access_key, aws_secret_key):
    try:
        ec2_resource = boto3.resource('ec2', region_name=region, aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key)
    except Exception, e:
        module.fail_json(msg="Could not return an EC2 resource " + str(e))
    return ec2_resource


def get_vpc_resource(module, vpc_id, ec2):
    try:
        vpc_resource = ec2.Vpc(vpc_id)
    except Exception, e:
        module.fail_json(msg="Could not return a VPC resource " + str(e))
    return vpc_resource


def get_vpc_subnets(module, vpc):
    try:
        subnet_iterator = vpc.subnets.all()
        subnets = list()
        for subnet in subnet_iterator:
            subnet_dict = dict()
            subnet_dict['id'] = subnet.id
            subnet_dict['cidr_block'] = subnet.cidr_block
            subnet_dict['tags'] = subnet.tags
            subnets.append(subnet_dict)
    except Exception, e:
        module.fail_json(msg="Could not return a subnet resources " + str(e))
    return subnets


def get_vpc_subnet_instances(module, ec2, vpc, subnets):
    try:
        all_instances = list()
        for subnet in subnets:
            subnet_id = subnet['id']
            subnet_resource = ec2.Subnet(subnet_id)
            instance_iterator = subnet_resource.instances.all()
            instances = list()
            for instance in instance_iterator:
                instance_dict = dict()
                instance_dict['id'] = instance.instance_id
                instance_dict['state'] = instance.state
                instance_dict['private_ip'] = instance.private_ip_address
                instance_dict['public_ip'] = instance.public_ip_address
                instance_dict['security_groups'] = instance.security_groups
                instance_dict['tags'] = instance.tags
                instances.append(instance_dict)
                all_instances.append(instance_dict)
            subnet['instances'] = instances
    except Exception, e:
        module.fail_json(msg="Could not return ec2 instance resources " + str(e))
    return subnets, all_instances


def get_vpc_route_tables(module, vpc):
    try:
        rt_iterator = vpc.route_tables.all()
        rts = list()
        for rt in rt_iterator:
            rt_dict = dict()
            rt_dict['id'] = rt.id
            rt_dict['routes'] = rt.routes
            rts.append(rt_dict)
    except Exception, e:
        module.fail_json(msg="Could not return route table resources " + str(e))
    return rts


def get_vpc_igw(module, vpc):
    try:
        igw_iterator = vpc.internet_gateways.all()
        igws = list()
        for igw in igw_iterator:
            igw_dict = dict()
            igw_dict['id'] = igw.id
            igws.append(igw_dict)
    except Exception, e:
        module.fail_json(msg="Could not return internet gateway resources " + str(e))
    return igws


def get_vpc_sec_groups(module, vpc):
    try:
        sg_iterator = vpc.security_groups.all()
        sgs = list()
        for sg in sg_iterator:
            sg_dict = dict()
            sg_dict['id'] = sg.group_id
            sg_dict['group_name'] = sg.group_name
            sg_dict['description'] = sg.description
            sgs.append(sg_dict)
    except Exception, e:
        module.fail_json(msg="Could not return security group resources " + str(e))
    return sgs


def get_empty_vpc(module, vpc):
    vpc_obj = dict()
    vpc_obj.update({'id': ""})
    vpc_obj.update({'subnets': []})
    vpc_obj.update({'route_tables': []})
    vpc_obj.update({'igw': []})
    vpc_obj.update({'security_groups': []})
    vpc_obj.update({'instances': []})
    # vpc_obj.update({'autoscale_groups': []})
    vpc_obj.update({'key_pairs': []})
    return vpc_obj


def get_vpc_asg(module, vpc_id, asg):
    asg_list = list()
    asg_iterator = asg.describe_auto_scaling_groups()
    for asg in asg_iterator['AutoScalingGroups']:
        asg_vpc = asg['VPCZoneIdentifier']
        if asg_vpc == vpc_id:
            asg_dict = dict()
            asg_dict['vpc_id'] = asg_vpc
            asg_dict['name'] = asg['AutoScalingGroupName']
            asg_dict['min_size'] = asg['MinSize']
            asg_dict['max_size'] = asg['MaxSize']
            asg_list.append(asg_dict)
    return asg_list


def get_keypairs(module, ec2):
    try:
        kp_iterator = ec2.describe_key_pairs()
        kps = list()
        for kp in kp_iterator['KeyPairs']:
            kp_dict = dict()
            kp_dict = kp
            kps.append(kp_dict)
    except Exception, e:
        module.fail_json(msg="Could not return key pair resources " + str(e))
    return kps


def main():
    argument_spec = ec2_argument_spec()
    argument_spec.update(dict(
        vpc_id=dict(type='str', default=None, required=False),
        name=dict(type='str', default=None, required=False),
        cidr_block=dict(type='str', default=None, required=False),
        aws_access_key=dict(type='str', default=None, required=True),
        aws_secret_key=dict(type='str', default=None, required=True),
    )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
    )

    if not HAS_BOTO3:
        module.fail_json(msg='boto is required for this module')

    vpc_id = module.params.get('vpc_id')
    name = module.params.get('name')
    cidr_block = module.params.get('cidr_block')
    aws_access_key_id = module.params.get('aws_access_key')
    aws_secret_access_key = module.params.get('aws_secret_key')

    changed = True

    region, ec2_url, aws_connect_params = get_aws_connection_info(module)

    if region:
        try:
            ec2_client = boto3.client('ec2', region_name=region, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
        except Exception, e:
            module.fail_json(msg="Boto3 client exception occurred: " + str(e))
    else:
        module.fail_json(msg="region must be specified")

    # Get VPC response from the client - this tells us if and how many exist
    vpc_response = get_vpc_response(module, ec2_client, name, cidr_block, vpc_id)

    print len(vpc_response['Vpcs'])

    # Check if VPC exists
    if (len(vpc_response['Vpcs']) == 1):

        # Get rid of response JSON overhead
        vpc_obj = vpc_response['Vpcs'][0]

        # Get a Boto3 ec2 client object
        ec2_client = get_ec2_boto3_client(module, region, aws_access_key_id, aws_secret_access_key)

        # Get a Boto3 ec2 resource object
        ec2_resource = get_ec2_resource(module, region, aws_access_key_id, aws_secret_access_key)

        # now get the resource to pass around using the id as a key
        vpc_id = vpc_obj['VpcId']
        vpc_resource = get_vpc_resource(module, vpc_id, ec2_resource)

        # Add key-value it was found
        vpc_obj.update({'found': 'true'})

        # Add legacy ID key for backwards compatibility
        vpc_obj.update({'id': vpc_id})

        # return a List of subnets and add as a Dict value
        vpc_subnets = get_vpc_subnets(module, vpc_resource)
        # vpc_obj.update({'subnets': vpc_subnets})

        # return a List of instances and add as a Dict value
        vpc_subnet_instances, vpc_all_instances = get_vpc_subnet_instances(module, ec2_resource, vpc_resource, vpc_subnets)
        vpc_obj.update({'subnets': vpc_subnet_instances})
        vpc_obj.update({'instances': vpc_all_instances})

        # return a List of route tables and add as a Dict value
        vpc_route_tables = get_vpc_route_tables(module, vpc_resource)
        vpc_obj.update({'route_tables': vpc_route_tables})

        # return a List of internet gateways and add as a Dict value
        vpc_igws = get_vpc_igw(module, vpc_resource)
        vpc_obj.update({'igw': vpc_igws})

        # return a List of security groups and add as a Dict value
        vpc_sg = get_vpc_sec_groups(module, vpc_resource)
        vpc_obj.update({'security_groups': vpc_sg})

        # Get a Boto3 autoscale group (asg) client resource
        asg_client = get_asg_boto3_client(module, region, aws_access_key_id, aws_secret_access_key)

        # return a List of autoscale groups and add as a Dict value
        vpc_asg = get_vpc_asg(module, vpc_id, asg_client)
        vpc_obj.update({'autoscale_groups': vpc_asg})

        # return a List of keyapris as a Dict value
        key_pairs = get_keypairs(module, ec2_client)
        vpc_obj.update({'key_pairs': key_pairs})

        # Return the results back to the module utility framework
        module.exit_json(changed=changed, vpc=vpc_obj)

    elif (len(vpc_response['Vpcs']) == 0):
        vpc_obj = get_empty_vpc(module, vpc_response)
        module.exit_json(changed=changed, vpc=vpc_obj)

    elif (len(vpc_response['Vpcs']) >= 2):
        module.fail_json(msg="more than one vpc was returned")

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.ec2 import *

if __name__ == '__main__':
    main()
