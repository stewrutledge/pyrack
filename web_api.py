#coding=utf-8
if __name__ != '__main__':
    from sys import path as syspath
    from os import path, chdir
    syspath.append(path.dirname(__file__))
    chdir(path.dirname(__file__))

from bottle import route, run, default_app, Bottle
from pyrack import RackConnect, RackObjects
from ConfigParser import ConfigParser

rackdb = ConfigParser()
rackdb.readfp(open('rackdb.conf'))
db_host = rackdb.get('mysql', 'hostname')
db_user = rackdb.get('mysql', 'user')
db_pass = rackdb.get('mysql', 'password')
db_name = rackdb.get('mysql', 'dbname')

rackdoc = RackConnect(
    mysql_host=db_host,
    user=db_user,
    password=db_pass,
    database=db_name
)
rackobjects = RackObjects(rackdoc)
app = Bottle()


@route('/facts/:obj_id')
def facts(obj_id=None):
    obj_id = int(obj_id)
    return rackobjects.obj_attr(obj_id)


@route('/name/:name')
def by_name(name=None):
    obj_id = int(rackobjects.get_id(from_type='name', value=name))
    return {'RackObj': rackobjects.obj_attr(obj_id)}


@route('/fqdn/:fqdn')
def by_fqdn(fqdn=None):
    obj_id = int(rackobjects.get_id(from_type='FQDN', value=fqdn))
    return rackobjects.obj_attr(obj_id)


@route('/withrole/:env/:role_id')
def with_role(role_id=None, env=None):
#    try:
        return rackobjects.with_role(role_id=role_id, environment=env)
#    except Exception as e:
#        return {"error": e.message}
if __name__ == '__main__':
    run(host='0.0.0.0', port=8282)
if __name__ != '__main__':
    application = default_app()
