# Description

`ec2_vpc_facts` is an Ansible module that discovers assets contained within an AWS VPC, and creates a JSON data structure mapping the relationships between discovered components. This module is a building block to represent VPC networking topologies.

The original version by dbhirko reports the error below:

TypeError: Value of unknown type: <class 'boto3.resources.factory.ec2.Route'>, ec2.Route(route_table_id='rtb-69ca4d0e', destination_cidr_block='172.22.0.0/16')

because `ec2_vpc_facts` returns a list of `ec2.Route` objects, but function `exit_json` in `lib/ansible/module_utils/basic.py` does not know about the ec2.Route class.

My quick fix: return a list of the dictionaries mapping `ec2.Route` objects.


# Variables

The module uses specific variables related to AWS credentials and regions that are intentionally eliminated from the included example.  Ansible describes several best practices to handle AWS Credentials [here](https://docs.ansible.com/ansible/guide_aws.html).  In the example, a `roles/vpc_facts/vars/main.yml` file contains these three variables in order to work:

* vpc_id: the unique VPC identifier for a previously launched AWS VPC
* ec2_region: the region for the VPC (eg `us-west-2`)
* aws_secret_key: the secret access key associated with an AWS credential
* aws_access_key: the public access key associated with an AWS credential

# Use

To launch the example included in this repo (after creating and populating the necessary variables):
```shell
ansible-playbook vpc_facts.yml
```

# Other Examples

There are two ways to query a VPC, the first, using the unique VPC identifier:
```yaml
- name: Get VPC Topology information using vpc-id
  ec2_vpc_facts:
    region: "{{ ec2_region }}"
    vpc_id: "{{ vpc_data.vpc.id }}"
  register: vpc_data
```
Sometimes, you may not know the `vpc_id`, especially immediately after provisioning, so we add a second way to discover and query the VPC using a combination of its `name` and `cidr_block` (note: this approach can be dangerous if you provision multiple VPC's with non-unique names):
```yaml
- name: Get VPC Topology information using name and CIDR block
  ec2_vpc_facts:
    region: "{{ ec2_region }}"
    cidr_block: "{{ vpc_cidr_block }}"
    name: "{{ vpc_name_tag }}"
  register: vpc_data
```

Once you have captured the output using Ansible's `register: vpc_data` module, its as easy as sending to the console:

```yaml
- name: Output contents of VPC
  debug: var=vpc_data
```

For more complex parsing scenarios in an Ansible playbook, such as building a list-object for specifically-tagged bastion VPC subnets, here is a sample Jinja2 snippet:

```yaml
- name: Find the Public Tagged Subnets
  set_fact:
    bastion_subnets: |
      {% set comma = joiner(",") %}
      [{% for subnet in vpc_data.vpc.subnets -%}
        {% for tag in subnet.tags %}
          {% if 'public' in tag.Value %}
            {{ comma() }}"{{ subnet.id }}"
          {% endif %}
        {% endfor %}
      {%- endfor %}]
```
Putting it all together, identifying a specific host and waiting for SSH to be enabled:
```yaml
- name: Find the Running Bastion Instances
  set_fact:
    bastion_ip: |
      {% set comma = joiner(",") %}
      [{% for instance in vpc_data.vpc.instances -%}
        {% for tag in instance.tags %}
          {% if 'bastion' in tag.Value %}
            {{ comma() }}"{{ instance.public_ip }}"
          {% endif %}
        {% endfor %}
      {%- endfor %}]

- name: Wait for SSH to open on bastion host
  wait_for: host={{ bastion_ip[0] }} port=22 state=present timeout=300 search_regex=OpenSSH delay=10

- name: Add bastion public ip address to bastion Group
  add_host: name={{ bastion_ip[0] }} groups='bastions'
  ```
