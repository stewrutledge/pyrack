#coding=utf-8
from ipaddress import ip_address, ip_network
from pymysql import connect


class _RackAPI:
    def __init__(self, mysql_host, user, password, database, charset='utf8'):
        self._conn =   {'host': mysql_host,
                       'user': user,
                       'pass': password,
                       'db': database,
                       'charset': charset}

    def _connect(self, connection):
        conn = connect(
                        host=self._conn['host'],
                        user=self._conn['user'],
                        passwd=self._conn['pass'],
                        db=self._conn['db'],
                        charset=self._conn['charset']
                      )
        self._cur = conn.cursor()

    def _is_dict(self, attr_name):
        self._connect(self._conn)
        try:
            self._cur.execute("SELECT Type from Attribute where name = '%s'" % attr_name)
            resp = self._cur.fetchall()
            if resp[0][0] == 'dict':
                return True
            if resp[0][0] != 'dict':
                return False
            self._cur.close()
        except:
            self._cur.close()
            return False

    def _get_dict(self, dict_key):
        self._connect(self._conn)
        self._cur.execute("SELECT dict_value from Dictionary where dict_key = %s" % dict_key)
        resp = self._cur.fetchall()
        self._cur.close()
        return resp[0]

    def _get_object(self, obj_id):
        self._connect(self._conn)
        self._cur.execute("SELECT name, asset_no FROM Object where id = %s" % obj_id)
        resp = self._cur.fetchall()
        data = {}
        data['asset'] = resp[0][1]
        data['name'] = resp[0][0]
        self._cur.close()
        return data

    def _gen_attr_map(self):
        self._connect(self._conn)
        self._cur.execute("SELECT * from Attribute")
        resp = self._cur.fetchall()
        attr_list = {}
        for attr in resp:
            attr_list[attr[0]] = attr[2]
        self._cur.close()
        return attr_list

    def _ipv4(self, obj_id):
        self._connect(self._conn)
        self._cur.execute("SELECT INET_NTOA(ip), mask, id from IPv4Network")
        networks = self._cur.fetchall()
        networks = [(['%s/%s' % (net[0], net[1]), net[2]]) for net in networks] 
        self._cur.execute("SELECT INET_NTOA(ip) from IPv4Allocation where object_id = %s" % obj_id)
        ipv4 = self._cur.fetchall()[0][0]
        ipv4_obj = ip_address(unicode(ipv4))
        self._cur.execute("SELECT INET_NTOA(ip) from IPv4Allocation where type = 'router'")
        routers = self._cur.fetchall()
        for network in networks:
            if ipv4_obj in ip_network(network[0]):
                payload = {'subnet': str(ip_network(network[0]).netmask), 'network': network[0], 'ipv4': ipv4}
                net_id = network[1]
                _network = ip_network(network[0])
                break
        gateways = []
        for router in routers:
            if ip_address(router[0]) in _network:
                gateways.append(router[0])
        payload.update({'gateways': gateways})
        return payload 

    def _get_attributes(self, obj_id=None):
        self._connect(self._conn)
        self._cur.execute("SELECT attr_id, string_value, uint_value from AttributeValue where object_id = %s" % obj_id)
        resp = self._cur.fetchall()
        if len(resp) > 0:
            obj_attr = {}
            attr_map = self._gen_attr_map()
            network_info = self._ipv4(obj_id)
            for item in resp:
                obj_mod = self._get_object(obj_id)
                obj_attr['Asset no'] = obj_mod['asset']
                obj_attr['Name'] = obj_mod['name']
                obj_attr['DNS'] = self._get_dns(obj_id)
                obj_attr['ipv4'] = {}
                obj_attr['ipv4']['ipaddress'] = network_info['ipv4']
                obj_attr['ipv4']['subnet'] = network_info['subnet']
                obj_attr['ipv4']['network'] = network_info['network']
                obj_attr['ipv4']['gateways'] = network_info['gateways']
                if self._is_dict(attr_map[item[0]]):
                    try:
                        obj_attr[attr_map[item[0]]] = self._get_dict(item[2])[0].split("%")[2]
                    except:
                        obj_attr[attr_map[item[0]]] = self._get_dict(item[2])[0]
                else:
                    try:
                        attr_list = item[1].split(",")
                        if len(attr_list) > 1:
                            obj_attr[attr_map[item[0]]] = attr_list
                        else:
                            obj_attr[attr_map[item[0]]] = item[1]
                    except AttributeError:
                        obj_attr[attr_map[item[0]]] = item[1]
        else:
            obj_attr = {'Name': None}
        self._cur.close()
        return obj_attr

    def _name_to_id(self, name=None):
        self._connect(self._conn)
        self._cur.execute("SELECT id FROM Object WHERE name = '%s'" % name)
        resp = self._cur.fetchall()
        self._cur.close()
        return resp[0][0]

    def _fqdn_to_id(self, fqdn=None):
        self._connect(self._conn)
        self._cur.execute("SELECT object_id FROM AttributeValue WHERE string_value = '%s' and attr_id = 3" % fqdn)
        resp = self._cur.fetchall()
        self._cur.close()
        return resp[0][0]

    def _get_dns(self, obj_id=None):
        self._connect(self._conn)
        self._cur.execute("SELECT INET_NTOA(ip) from IPv4Allocation where object_id = %s" % obj_id)
        resp = self._cur.fetchall()
        if ip_address(unicode(resp[0][0])).is_private:
            tag_id = 3
        if not ip_address(unicode(resp[0][0])).is_private:
            tag_id = 4
        self._cur.execute("SELECT entity_id from TagStorage where tag_id = %s" % tag_id)
        resp = self._cur.fetchall()
        obj_list = ["object_id = %s" % obj[0] for obj in resp]
        with_ors = " OR ".join(obj_list)
        self._cur.execute("SELECT INET_NTOA(ip) FROM IPv4Allocation WHERE %s" % with_ors)
        resp = self._cur.fetchall()
        self._cur.close()
        return [ipv4[0] for ipv4 in resp]


class RackConnect(_RackAPI):
    def RackConnect(self, mysql_host, user, password, database):
        _RackAPI.__init__(mysql_host=mysql_host, user=user, password=password, database=database)


class RackObjects(object):
    def __init__(self, rack):
        self.rack = rack

    def get_id(self, from_type=None, value=None):
        if from_type == 'FQDN':
            return self.rack._fqdn_to_id(value)
        if from_type == 'name':
            return self.rack._name_to_id(value)

    def obj_attr(self, obj_id=None):
        if not isinstance(obj_id, int):
            return("Object ID must be an integer")
        elif isinstance(obj_id, int):
            return self.rack._get_attributes(obj_id)

