#coding=utf-8
from bottle import route, run
from pyrack import RackConnect, RackObjects


rackdoc = RackConnect(mysql_host='localhost', user='rack', password='rack', database='rack_test')
rackobjects = RackObjects(rackdoc)

@route('/facts/:obj_id')
def facts(obj_id=None):
#    try:
        obj_id = int(obj_id)
        return rackobjects.obj_attr(obj_id)
#    except ValueError:
#        return {'message': 'Object ID must be an integer'}

@route('/name/:name')
def by_name(name=None):
#    try:
        obj_id = int(rackobjects.get_id(from_type='name', value=name))
        return {'RackObj': rackobjects.obj_attr(obj_id)}

@route('/fqdn/:fqdn')
def by_fqdn(fqdn=None):
    obj_id = int(rackobjects.get_id(from_type='FQDN', value=fqdn))
    return rackobjects.obj_attr(obj_id)
#    except:
#        return {'RackObj': 'could not find name!'}

@route('/withrole/:env/:role_id')
def with_role(role_id=None,env=None):
    try:
        return rackobjects.with_role(role_id=role_id, environment=env)
    except:
        return {}
run(host='0.0.0.0', port=8080)
