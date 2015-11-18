# Description

`ec2_vpc_facts` is an Ansible module that discovers assets contained within an AWS VPC, and creates a JSON data structure mapping the relationships between discovered components. This module is a building block to represent VPC networking topologies. As any AWS customer knows, it is not easy to manage assets in the AWS Web Console beyond a few instances. Ansible has a [AWS inventory module](https://docs.ansible.com/ansible/intro_dynamic_inventory.html#example-aws-ec2-external-inventory-script) that *only* lists servers. We needed something a little more robust (and faster) to map the relationships of virtual instances to other components such as subnets, security groups, and asset tags.

Last year, we accomplished this using POJO's and the AWS Java SDK, but it required a lot more code, did not facilitate easy re-use, and was not as accessible to a broader set of tasks. Ansible and YAML playbooks changed that for us. Our requirement was to model the current as-is VPC topology as a JSON data structure to include the AWS unique identifiers and other relevant metadata. The output could then be parsed, used as input for other Ansible modules, or transformed for use in other ways. As the VPC topologies change over time, we could  run this Ansible module on a regular basis and keep our topology representation up-to-date. Currently, we discover the following assets, the associated relevant metadata, and map their relationships in a single JSON data structure:


* Virtual Private Clouds
* Subnets
* Route Tables
* Routes
* Internet Gateways
* AutoScale Groups
* EC2 Instances
* Key Pairs
* Security Groups
* IP Addresses
* Resource Tags

# Boto Dependency

Our module currently imports Amazon's Boto2 and [Boto3](https://github.com/boto/boto3) Python libraries.  All of the module code uses the new Boto3 library as it closely parallels many of the relationships we wanted exposed in our JSON data structure. [As Ansible moves to its major 2.0 release, we maintain backwards compatibility with Boto2](https://github.com/ansible/ansible/issues/13010), but hope to deprecate Boto2 soon.   Using Boto3, we can quickly add new items to the topology data structure based on customer needs.

# Variables

The module uses specific variables related to AWS credentials and regions that are intentionally eliminated from the included example.  Ansible describes several best practices to handle AWS Credentials [here](https://docs.ansible.com/ansible/guide_aws.html).  In the example, a vars/main.yml file contains these three variables in order to work:

* vpc_id: the unique VPC identifier for a previously launched AWS VPC
* ec2_region: the region for the VPC (eg `us-west-2`)
* aws_secret_key: the secret access key associated with an AWS credential
* aws_access_key: the public access key associated with an AWS credential

# Use

To launch the example included in this repo (after creating and populating the necessary variables):

`ansible-playbook vpc_facts.yml`

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
