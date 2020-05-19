import gdb

class QStringPrinter:
    def __init__(self, val):
        self.val = val

    def to_string(self):
        d = self.val['d']
        char_type = gdb.lookup_type('char')
        data = d.cast(char_type.pointer()) + d['offset']
        return data.string(encoding = 'UTF-16', length = d['size'] * 2)

class QVectorPrinter:
    class _iterator:
        def __init__(self, data, size):
            self.data = data
            self.size = size
            self.index = 0

        def __iter__(self):
            return self

        def __next__(self):
            if self.index >= self.size:
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
            if self.index >= self.size:
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

def build_pretty_printer():
    pp = gdb.printing.RegexpCollectionPrettyPrinter('Qt5')
    pp.add_printer('QString', '^QString$', QStringPrinter)
    pp.add_printer('QVector', '^QVector<.*>$', QVectorPrinter)
    pp.add_printer('QList', '^QList<.*>$', QListPrinter)
    return pp
