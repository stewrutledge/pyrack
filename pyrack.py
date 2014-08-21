#coding=utf-8
from ipaddress import ip_address, ip_network
from pymysql import connect
import struct
from socket import inet_aton


class RackError:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class _RackAPI:
    def __init__(
            self, mysql_host,
            user, password,
            database, charset='utf8',
            **kw):
        self._conn = {'host': mysql_host,
                      'user': user,
                      'pass': password,
                      'db': database,
                      'charset': charset}
        self.fqdnID = kw.get('fqdnID', 10003)
        self.ansibleTag = kw.get('ansibleTag', 3)

    def _connect(self, connection):
        conn = connect(
            host=self._conn['host'],
            user=self._conn['user'],
            passwd=self._conn['pass'],
            db=self._conn['db'],
            charset=self._conn['charset']
        )
        self._cur = conn.cursor()

    def _get_dict(self, dict_key):
        self._connect(self._conn)
        self._cur.execute(
            "SELECT dict_value from Dictionary where dict_key = %s",
            (dict_key, )
        )
        resp = self._cur.fetchall()
        self._cur.close()
        return resp[0]

    def _get_object(self, obj_id):
        self._connect(self._conn)
        self._cur.execute(
            "SELECT name, asset_no FROM Object where id = %s", (obj_id, )
        )
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
        self._cur.close()
        attr_dict = {}
        for attr in resp:
            attr_dict[attr[0]] = [attr[1], attr[2]]
        return attr_dict

    def _ipv4(self, obj_id):
        self._connect(self._conn)
        self._cur.execute("SELECT INET_NTOA(ip), mask, id from IPv4Network")
        networks = self._cur.fetchall()
        networks = [(['%s/%s' % (net[0], net[1]), net[2]]) for net in networks]
        self._cur.execute("""
            SELECT INET_NTOA(ip) from
            IPv4Allocation where object_id = %s""", (obj_id, ))
        try:
            ipv4 = self._cur.fetchall()[0][0]
            ipv4_obj = ip_address(unicode(ipv4))
            router_sql = """SELECT
                          INET_NTOA(ip)
                          from IPv4Allocation
                          where INET_NTOA(ip)
                          like '%s.%s' AND type = 'shared'
                          """ % ((".").join(ipv4.split('.')[:+3]), '%')
            self._cur.execute(router_sql)
            routers = self._cur.fetchall()
            if len(routers) == 0:
                router_sql = """SELECT
                              INET_NTOA(IP)
                              from IPv4Allocation
                              where INET_NTOA(ip)
                              LIKE '%s.%s'
                              """, ((".").join(ipv4.split('.')[:+3]), '%')
                self._cur.execute(router_sql)
                routers = self._cur.fetchall()
            for network in networks:
                if ipv4_obj in ip_network(unicode(network[0])):
                    ipv4net = ip_network(unicode(network[0]))
                    aton = struct.unpack(
                        "!I",
                        inet_aton(ipv4net.network_address.exploded)
                    )[0]
                    self._cur.execute("""
                        SELECT id FROM IPv4Network
                        WHERE ip = %s
                        """, (aton, ))
                    ipq_res = self._cur.fetchone()
                    self._cur.execute("""SELECT vlan_id FROM
                             VLANIPv4 where ipv4net_id = %s
                            """, (ipq_res[0], ))
                    vlanq_res = self._cur.fetchone()
                    self._cur.execute("""SELECT vlan_descr FROM
                                   VLANDescription WHERE
                                   vlan_id = %s""", (vlanq_res,))
                    vlannameq_res = self._cur.fetchone()
                    payload = {
                        'subnet': str(ipv4net.netmask),
                        'network': network[0],
                        'ipv4': ipv4,
                        'vlanName': vlannameq_res[0]
                    }
                    _network = ip_network(unicode(network[0]))
                    break
            for router in routers:
                if ip_address(unicode(router[0])) in _network:
                    payload['gateway'] = router[0]
                    break
            return payload
        except Exception as e:
            print e
            return {
                'subnet': None, 'network': None,
                'ipv4': None, 'gateway': None
            }

    def _gen_role_dict(self):
        self._connect(self._conn)
        self._cur.execute("SELECT id, tag from TagTree")
        resp = self._cur.fetchall()
        role_dict = {}
        for role in resp:
            role_dict[role[0]] = role[1]
        return role_dict

    def _get_roles(self, obj_id=None):
        role_dict = self._gen_role_dict()
        self._connect(self._conn)
        try:
            self._cur.execute(
                "SELECT tag_id from TagStorage where entity_id = %s",
                (obj_id, )
            )
            resp = self._cur.fetchall()
        except:
            resp = []
        roles = []
        for role in resp:
            roles.append(role_dict[role[0]])
        return roles

    def _get_attributes(self, obj_id=None):
        self._connect(self._conn)
        self._cur.execute("""
            SELECT attr_id, string_value, uint_value
            from AttributeValue where object_id = %s""", (obj_id, ))
        resp = self._cur.fetchall()
        if len(resp) > 0:
            obj_attr = {}
            attr_map = self._gen_attr_map()
            network_info = self._ipv4(obj_id)
            for item in resp:
                print item
                attr_name = attr_map[item[0]][1]
                attr_type = attr_map[item[0]][0]
                obj_mod = self._get_object(obj_id)
                obj_attr['Asset no'] = obj_mod['asset']
                obj_attr['Name'] = obj_mod['name']
                obj_attr['Roles2'] = self._get_roles(obj_id)
                try:
                    obj_attr['DNS'] = self._get_dns(obj_id)
                except:
                    obj_attr['DNS'] = None
                obj_attr['ipv4'] = {}
                obj_attr['ipv4']['ipaddress'] = network_info['ipv4']
                obj_attr['ipv4']['subnet'] = network_info['subnet']
                obj_attr['ipv4']['network'] = network_info['network']
                obj_attr['ipv4']['gateway'] = network_info['gateway']
                obj_attr['ipv4']['vlan'] = network_info['vlanName']
                obj_attr['obj_id'] = obj_id
                if attr_type == 'dict':
                    obj_attr[attr_name] = self._get_dict(item[2])[0]
                    try:
                        obj_attr[attr_name] = obj_attr[attr_name].split("%")[2]
                    except:
#                        obj_attr[attr_name] = self._get_dict(item[2])[0]
                        pass
                else:
                    try:
                        attr_list = item[1].split(",")
                        if len(attr_list) > 1:
                            obj_attr[attr_name] = attr_list
                        else:
                            if item[1] is None:
                                obj_attr[attr_name] = item[2]
                            else:
                                obj_attr[attr_name] = item[1]
                    except AttributeError:
                        obj_attr[attr_name] = item[2]
        else:
            obj_attr = {'Name': None}
        self._cur.close()
        return obj_attr

    def _get_tag_id(self, tagString):
        self._connect(self._conn)
        self._cur.execute(
            'select id from TagTree where tag = %s', (tagString, )
        )
        resp = self._cur.fetchone()
        if resp:
            return resp[0]
        else:
            return None

    def _with_tag(self, tagString):
        tagID = self._get_tag_id(tagString)
#        tagList = []
        if tagID is not None:
            self._cur.execute(
                'select entity_id from TagStorage where tag_id = %s',
                (tagID, )
            )
            tresp = self._cur.fetchall()
        else:
            tresp = ''
        if len(tresp) > 0:
            searchIDs = [id[0] for id in tresp]
            query = ("""
                SELECT name
                FROM Object
                WHERE id in (%s)""")
            inTransform = ', '.join(map(lambda x: '%s', searchIDs))
            query = query % inTransform
            self._cur.execute(query, searchIDs)
            withTagResp = self._cur.fetchall()
        else:
            withTagResp = []
        if len(withTagResp) > 0:
            return([name[0] for name in withTagResp])
        else:
            return([])

    def _with_role(self, role_id=None, environment=None):
        role_dict = self._gen_role_dict()
        self._connect(self._conn)
        self._cur.execute(
            "SELECT dict_key from Dictionary where dict_value = %s",
            (environment, )
        )
        env_resp = self._cur.fetchall()
        if len(env_resp) == 0:
            raise KeyError("Could not get environment ID, does it exist?")
        env_id = env_resp[0]
        self._connect(self._conn)
        self._cur.execute(
            """SELECT entity_id, tag_id
            FROM `TagStorage`
            where entity_id = ANY (
                SELECT entity_id from `TagStorage`) AND tag_id = ANY (
                  SELECT id from `TagTree` where parent_id = %s
                )
             AND entity_id = ANY (
            select object_id from AttributeValue where uint_value = %s)""",
            (role_id, env_id)
        )
        role_resp = self._cur.fetchall()
        if len(role_resp) == 0:
            raise KeyError("No hosts found")
        roles = {}
        fqdns = {}
        self._connect(self._conn)
        searchIDs = [int(obj_id[0]) for obj_id in role_resp]

        #print searchIDs
        query = ("""
            SELECT name, id
            FROM Object
            WHERE id in (%s)""")
        inTransform = ', '.join(map(lambda x: '%s', searchIDs))
        query = query % inTransform
        self._cur.execute(query, searchIDs)
        resp = self._cur.fetchall()
        #print self._cur._last_executed
        #print resp
        for fqdn in resp:
            fqdns[fqdn[1]] = fqdn[0]
        #print fqdns
        for role in role_resp:
          #  print role
            try:
                roles[role_dict[role[1]]]
            except KeyError:
                roles[role_dict[role[1]]] = []
            roles[role_dict[role[1]]].append(fqdns[role[0]])
        roles['_meta'] = {}
        roles['_meta']['hostvars'] = {}
        hostVars = roles['_meta']['hostvars']
        for obj_id in searchIDs:
            network_info = self._ipv4(obj_id)
            hostVars[fqdns[obj_id]] = {
                'ansible_ssh_host': network_info['ipv4']
            }
        for obj_id in searchIDs:
            self._cur.execute("""
                select string_value from AttributeValue where
                object_id = %s and attr_id = %s""", (obj_id, self.fqdnID))
            resp = self._cur.fetchone()
            print self._cur._last_executed

            print resp
            if resp:
                extraVars = resp[0].split()
                for var in extraVars:
                    k, v = var.split('=')
                    hostVars[fqdns[obj_id]][k] = v
        return roles

    def _name_to_id(self, name=None):
        self._connect(self._conn)
        self._cur.execute("SELECT id FROM Object WHERE name = '%s'", (name, ))
        resp = self._cur.fetchone()
        self._cur.close()
        if len(resp) == 0:
            raise RackError('Could not find %s' % name)
        return resp[0]

    def _fqdn_to_id(self, fqdn=None):
        self._connect(self._conn)
        self._cur.execute("""
            SELECT object_id FROM AttributeValue WHERE string_value = '%s'
            and attr_id = %s
            """, (fqdn, self.ansibleTag)
        )
        resp = self._cur.fetchone()
        self._cur.close()
        if len(resp) == 0:
            raise RackError('Could not find %s' % fqdn)
        return resp[0]

    def _get_dns(self, obj_id=None):
        self._connect(self._conn)
        self._cur.execute("""
            SELECT INET_NTOA(ip) from
            IPv4Allocation where object_id = %s
            """, (obj_id, )
        )
        resp = self._cur.fetchall()
        if ip_address(unicode(resp[0][0])).is_private:
            tag_id = 3
        if not ip_address(unicode(resp[0][0])).is_private:
            tag_id = 4
        self._cur.execute("""
            SELECT entity_id from
            TagStorage where tag_id = %s
            """, (tag_id, )
        )
        resp = self._cur.fetchall()
        #obj_list = ["object_id = %s" % obj[0] for obj in resp]
        obj_list = [obj[0] for obj in resp]
        inTransform = ', '.join(map(lambda x: '%s', obj_list))
        #with_ors = " OR ".join(obj_list)
        query = ("""
            SELECT INET_NTOA(ip) FROM
            IPv4Allocation WHERE %s object_id in (%s)
        """)
        query = query % inTransform
        self._cur.execute(query, obj_list)
        resp = self._cur.fetchall()
        self._cur.close()
        return [ipv4[0] for ipv4 in resp]


class RackConnect(_RackAPI):
    def RackConnect(self, mysql_host, user, password, database):
        _RackAPI.__init__(
            mysql_host=mysql_host,
            user=user,
            password=password,
            database=database
        )


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

    def with_tag(self, tagString):
        return(self.rack._with_tag(tagString))

    def with_role(self, role_id=None, environment=None):
        return self.rack._with_role(role_id=role_id, environment=environment)
