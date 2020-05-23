import gdb

class QStringPrinter:
    def __init__(self, val):
        self.val = val

    def to_string(self):
        d = self.val['d']
        char_type = gdb.lookup_type('char')
        data = d.cast(char_type.pointer()) + d['offset']
        return data.string(encoding = 'UTF-16', length = d['size'] * 2)

    def display_hint(self):
        return 'string'

class QVectorPrinter:
    class _iterator:
        def __init__(self, data, size):
            self.data = data
            self.size = size
            self.index = 0

        def __iter__(self):
            return self

        def __next__(self):
            if self.index == self.size:
                raise StopIteration
            index = self.index
            self.index += 1
            return ('[%d]' % index, self.data[index])

    def __init__(self, val):
        self.val = val
        self.value_type = self.val.type.template_argument(0)

    def to_string(self):
        d = self.val['d']
        return 'QVector<%s> of length %d' % (self.value_type, d['size'])

    def children(self):
        d = self.val['d']
        char_type = gdb.lookup_type('char')
        data = (d.cast(char_type.pointer()) + d['offset']).cast(self.value_type.pointer())
        return self._iterator(data, d['size'])

    def display_hint(self):
        return 'array'

class QListPrinter:
    class _iterator:
        def __init__(self, data, value_type, size):
            self.data = data
            self.value_type = value_type
            self.size = size
            self.index = 0

        def __iter__(self):
            return self

        def __next__(self):
            if self.index == self.size:
                raise StopIteration
            index = self.index
            self.index += 1
            void_pointer_type = gdb.lookup_type('void').pointer()
            if self.value_type.sizeof > void_pointer_type.sizeof:
                # QTypeInfo<T>::isLarge
                value = self.data[index].cast(self.value_type.pointer()).dereference()
            else:
                value = self.data[index].cast(self.value_type)
            return ('[%d]' % index, value)

    def __init__(self, val):
        self.val = val
        self.value_type = self.val.type.template_argument(0)

    def to_string(self):
        d = self.val['d']
        size = d['end'] - d['begin']
        return 'QList<%s> of length %d' % (self.value_type, size)

    def children(self):
        d = self.val['d']
        void_type = gdb.lookup_type('void')
        data = d['array'].cast(void_type.pointer().pointer()) + d['begin']
        size = d['end'] - d['begin']
        return self._iterator(data, self.value_type, size)

    def display_hint(self):
        return 'array'

class QMapPrinter:
    class _iterator:
        def __init__(self, node_type, header):
            self.node_type = node_type
            self.header = header
            self.index = 0
            node = header['left']
            if node:
                while node['left']:
                    node = node['left']
            self.node = node

        def __iter__(self):
            return self

        def __next__(self):
            if not self.node or self.node == self.header.address:
                raise StopIteration
            typed_node = self.node.cast(self.node_type.pointer())
            if self.index % 2 == 0:
                value = typed_node['key']
            else:
                value = typed_node['value']
                self.next_node()
            index = self.index
            self.index += 1
            return ('[%d]' % index, value)

        def next_node(self):
            def parent_node(node):
                node_type = gdb.lookup_type('QMapNodeBase')
                return (node['p'] & ~3).cast(node_type.pointer())
            n = self.node
            if n['right']:
                n = n['right']
                while n['left']:
                    n = n['left']
            else:
                y = parent_node(n)
                while y and n == y['right']:
                    n = y
                    y = parent_node(n)
                n = y
            self.node = n

    def __init__(self, val):
        self.val = val;
        self.key_type = self.val.type.template_argument(0)
        self.value_type = self.val.type.template_argument(1)

    def to_string(self):
        d = self.val['d']
        size = d['size']
        return 'QMap<%s, %s> of size %d' % (self.key_type.name, self.value_type.name, size)

    def children(self):
        node_type = gdb.lookup_type('QMapNode<%s,%s>' % (self.key_type.name, self.value_type.name))
        header = self.val['d']['header']
        return self._iterator(node_type, header)

    def display_hint(self):
        return 'map'

def build_pretty_printer():
    pp = gdb.printing.RegexpCollectionPrettyPrinter('Qt5')
    pp.add_printer('QString', '^QString$', QStringPrinter)
    pp.add_printer('QVector', '^QVector<.*>$', QVectorPrinter)
    pp.add_printer('QList', '^QList<.*>$', QListPrinter)
    pp.add_printer('QMap', '^QMap<.*>$', QMapPrinter)
    return pp
