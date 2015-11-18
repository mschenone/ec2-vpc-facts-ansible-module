*A blog post describing our open source Ansible module for discovering relationships in an AWS Virtual Private Cloud. -By Dave Hirko*

## Launching in the Cloud?

At B23 we build, implement, and configure a lot of applications for Fortune 500 customers with sensitive data that reside natively in *The Cloud*.  This Fall, and in the run up to Amazon Web Services (AWS) 2015 Re:Invent marketing conference, we observed many companies from many industries claiming that they could *Launch in the Cloud.*  To us, *Launching in the Cloud* is about as ambiguous as the term *Cloud* itself.  Having spent many years working with AWS technologies, we were curious...

## Security Anyone?

We started to notice that most of these applications were critically flawed in addressing basic security once they were *Launched in the Cloud.*  It wasn't that AWS was insecure, but that these applications were not using the services AWS makes available to make them secure in the first place.  For example, most of the application EC2 hosts were assigned Public Internet Protocol (IP) addresses which made them accessible to anyone on the Internet.  Unlike tradition networks that exhibit some form of defense-in-depth, they did not take advantage of AWS' powerful software-defined networking (SDN) subnet and routing capabilities found within a Virtual Private Cloud (VPC).  In one specific case, an application launched a Hadoop cluster where every node in the cluster was allocated a public Elastic IP address.  Yikes!  For us, that's either negligent or lazy, or both.  Given our experience that AWS Public IP addresses become a target within seconds of existing (launch a Tomcat server using TCP/8080, then check your log files), we believe this type of deployment model is inherently flawed.  Amazon's Simple Storage Service, or S3, was another major security challenge for most of these *Launched in the Cloud* applications.  S3 has a very robust policy engine that allows for almost any conceivable way to securing its data contents, yet we still continued to find improperly configured S3 buckets.  Some of these S3 buckets were open to the Internet, and almost all without automated access control policy enforcement.  In essence, most of these applications were **one button-click** away from having their contents exposed to the world, and relied on a human to validate, enforce, and monitor the policy.  Not to mention that no one was using autoscale, automated tagging of assets, or custom endpoints.

For background, AWS' philosophy around security is based on a principle called the [Shared Responsibility Model](https://aws.amazon.com/compliance/shared-responsibility-model/).  AWS provides security for the physical assets and portions of the logical assets up to and including the hypervisor.  AWS customers are therefore responsible for securing all aspects of their hosted applications.  This include the guest host operating system and all software that resides on that operating system.  The AWS model is very pragmatic, and AWS provides a remarkable number of services for securing hosted applications.  There are now so many security-related options that we believe a properly configured Cloud hosted application can be *more secure* on AWS than its on-premise analog.  This model relies on its customers to implement these services in the proper way in order to maintain a certain level of security.  There is still an element of programming expertise and domain knowledge required to effectively secure hosted applications.  We wanted to take one step closer to fix that.

## Security Starts with the Network

We believe security starts with the network, and the AWS VPC is the *network shell* to enable a layered set of capabilities to make hosted applications inherently more secure.  Historically, network management involved discovering assets and understanding their relationships using the Simple Network Management Protocol (SNMP).  SNMP was an underpinning for discovering assets and visualizing their relationships. SNMP does not exist in AWS for good reason, and we have access to this same (and more) underlying relationship information via API's.  

Autoscale and dynamic provisioning of resources breaks the old paradigm for maintaining static inventories of assets.  We cannot afford the luxury of maintaining static inventories while taking advantage of dynamically allocated horizontal scale-out workloads.  Pets vs. Cattle.

At B23, we use Ansible to implement most of our automated provisioning and configurations.  There are many reasons we prefer Ansible at the present to other tools (which could be a discussion onto itself). One of those reasons is that when you need a brand new capability that does not exist in the Ansible module library, its very easy to build one yourself using the native Python API's.  Another is that Ansible is very good at provisioning Cloud resources while still maintaining some degree of autonomy and avoiding Cloud-vendor lock-in.  Ansible has proven itself to be easy to use and understand, flexible, and supports every layer of the stack that requires provisioning and configuration.   We only need one tool to support almost every conceivable automation task.

Knowing the network and its assets, we can then apply security policies consistently, and most important, automatically.

## Announcing ec2_vpc_facts Ansible Module

Today we are open sourcing a custom developed Ansible module we call `ec2_vpc_facts` that discovers assets contained within a VPC, and creates a JSON data structure mapping the relationships between discovered components.  This module is a building block to represent VPC networking topologies in different ways. As any AWS customer knows, it is not easy to manage assets in the AWS Web Console beyond a few instances.  Ansible has a AWS inventory module that only *discovers* servers.  We needed something a little more robust (and faster) to map the relationships of servers to other components such as subnets, security groups, and asset tags.  Last year, we accomplished this using POJO's and the AWS Java SDK, but it required a lot more code and was not as accessible to a broader set of tasks. Ansible and YAML playbooks changed that for us. Our requirement was to model the current as-is VPC topology as a JSON data structure to include the AWS unique identifiers and other relevant metadata.  Since  output could then be parsed, further interrogated, or imported for use in other ways.  As the VPC topology changed over time, we could then run this Ansible module on a regular basis and keep our topology representation up-to-date.  Currently, we discover the following assets, the associated relevant metadata, and map their relationships in a single JSON data structure:

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

Our module currently imports Amazon's Boto2 and Boto3 Python libraries.  All of the module code uses the new Boto3 library as it closely parallels many of the relationships we wanted exposed in our JSON data structure. As Ansible moves to its major 2.0 release, we maintain backwards compatibility with Boto2, but hope to deprecate Boto2 soon.   Using Boto3, we can quickly add new items to the topology data structure based on customer needs.  

## Here's How It Works...

There are two ways to query a VPC, the first, using the unique VPC identifier:
```
- name: Get VPC Topology information using vpc-id
  ec2_vpc_facts:
    region: "{{ ec2_region }}"
    vpc_id: "{{ vpc_data.vpc.id }}"
  register: vpc_data
```
Sometimes, you may not know the `vpc-id`, especially immediately after provisioning, so we add a second way to discover and query the VPC using a combination of its `name` and `cidr_block` (note: this approach can be dangerous if you provision multiple VPC's with non-unique names):
```
- name: Get VPC Topology information using name and CIDR block
  ec2_vpc_facts:
    region: "{{ ec2_region }}"
    cidr_block: "{{ vpc_cidr_block }}"
    name: "{{ vpc_name_tag }}"
  register: vpc_data
```

Once you have captured the output using Ansible's `register: vpc_data` module, its as easy as sending to the console:

```
- name: Output contents of VPC
  debug: var=vpc_data
```

For more complex parsing scenarios in an Ansible playbook, such as building a list-object for specifically-tagged bastion VPC subnets, here is a sample Jinja2 snippet:

```
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
```
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

## Future Work and Ideas

We have already started to design and implement similar modules for Google's Cloud Networking SDN, as well as for Microsoft Azure's Virtual Network SDN.  By creating similar JSON data structures representing Cloud-agnostic SDN topologies, we believe this will facilitate more re-use of existing Ansible playbooks for consistently securing applications that want to *Launch in the Cloud.*

*About the Author: Dave is a Co-Founder and Partner at B23.  Prior to founding B23, Dave worked at Amazon Web Services (AWS) for several years.  Dave has held a number of engineering and account executive roles in both large and small technology companies.  Dave earned a BS in Electrical Engineering from the University of Virginia, and an MBA from the University of Maryland at College Park.*
