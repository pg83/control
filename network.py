import dbus

bus = dbus.SystemBus()

def raw(path):
    return bus.get_object('org.freedesktop.NetworkManager', path)


class Object(object):
    def __init__(self, path):
        self.raw = raw(path)
        self.path = path
        self.map = {}
        self.props = {}

        def before(sep, line):
            return line[:line.find(sep)]

        def after(sep, line):
            return line[line.find(sep) + len(sep):]

        def name(line):
            return before('"', after('name="', line))

        cur = None

        for line in self.introspect().split('\n'):
            if '<interface' in line:
                cur = name(line)
            elif '<method' in line:
                self.map[name(line)] = cur
            elif '<property' in line:
                self.props[name(line)] = cur


    def interface(self, face):
        return dbus.Interface(self.raw, face)


    def introspect(self):
        return self.raw.Introspect()


    def getpath(self):
        return self.path


    def __getattr__(self, name):
        if name in self.map:
            return getattr(self.interface(self.map[name]), name)

        if name in self.props:
            return self.Get(self.props[name], name)


    def __repr__(self):
        return '<' + self.path + '>'


class NetworkManager(Object):
    def __init__(self):
        Object.__init__(self, '/org/freedesktop/NetworkManager')


    def devices(self):
        for path in self.GetDevices():
            yield Object(path)


class Settings(Object):
    def __init__(self):
        Object.__init__(self, '/org/freedesktop/NetworkManager/Settings')


    def find(self, id):
        for conn in self.ListConnections():
            conn = Object(conn)

            for x, y in dict(conn.GetSettings()).items():
                if y.get('id', None) == id:
                    return conn


srv = NetworkManager()

cpath = Settings().find('yandex network').getpath()
dpath = None

for dev in srv.devices():
    if dev.DeviceType == 2:
        dpath = dev.getpath()


srv.ActivateConnection(cpath, dpath, '/')
