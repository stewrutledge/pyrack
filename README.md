# Pyrack

A basic (for now) library for interfacing with the racktables database.

Requires pymsql and iptables to be installed.

There are, of course, quite a static values in here and there is no guarentee that it will work right away. A few things that are there that could be better:

The attribute ID of fqdn is set to 3, right now this is a hardcoded value however that is also the default value on a vanilla racktables install.

For host exports there is a static tag value for internal and external DNS servers, obviously this doesn't exist in everyones environment and needs to be fixed.


## Usage

```python
from pyrack import RackConnect, RackObjects

racktables = RackConnect(mysq_host='yourhost', user='dbuser', password='supersecret', database='databasename')
rackobj = RackObjects(racktables)

print rackobj.with_role(role_id=4, environment='staging')
```

This will print an ansible formatted inventory, where role_id is the parent tag for ansible configuration (like so)

```
ansible
  -> mariadb
  -> dns_server
  -> base_config
```

## Notes

A basic web api is included which will, at very least, allow you to export an ansible formatted inventory file via:
  http://yourhost/<environment>/<parent_tag_id>

Output is provided in json:

```json
{
  'tag1': [
   'host1',
   'host2'
  ],
  'tag2': [
   'host1',
   'host3'
  ]
}
```
