import dbus
from dbus.mainloop.glib import DBusGMainLoop
import gobject

DBusGMainLoop(set_as_default = True)

bus = dbus.SystemBus()

def raw(path):
    return bus.get_object('org.freedesktop.NetworkManager', path)


class Object(object):
    def __init__(self, path):
        self.raw = raw(path)
        self.path = path
        self.map = {}
        self.props = {}
        self.signals = {}

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
            elif '<signal' in line:
                self.signals[name(line)] = cur


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

        if name in self.signals:
            def sigset(handler):
                def wrapper(*args, **kwargs):
                    handler(self, *args, **kwargs)

                self.interface(self.signals[name]).connect_to_signal(name, wrapper)

            return sigset


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


    def vpn(self):
        return self.find('yandex network')


NM = NetworkManager()
BC = None

def bestchannel():
    cur = None
    ret = None

    for dev in NM.devices():
        if dev.State == 100:
            if dev.DeviceType == 2:
                if 'PDAS' in dev.GetAccessPoints():
                    return None

            if not cur or cur > dev.DeviceType:
                cur = dev.DeviceType
                ret = dev

    return ret

def onstate(obj, *args, **kwargs):
    global BC

    dpath = bestchannel()
    cpath = Settings().vpn()

    if not cpath:
        print 'no vpn'

        return

    cpath = cpath.getpath()

    if dpath:
        dpath = dpath.getpath()

        if dpath != BC:
            print 'activate', cpath, dpath
            NM.ActivateConnection(cpath, dpath, '/')
            BC = dpath
    else:
        print 'deactivate', cpath

        try:
            NM.DeactivateConnection(cpath)
        except Exception as e:
            print e

onstate(None)

NM.StateChanged(onstate)

for dev in NM.devices():
    dev.StateChanged(onstate)

    if dev.DeviceType == 2:
        dev.AccessPointAdded(onstate)
        dev.AccessPointRemoved(onstate)

gobject.MainLoop().run()
