import weakref


class GraphNode:
    def __init__(self, data):
        self.data = data

    def get_pyority(self):
        method = self.data.getattr('pyority', None)
        if method is not None:
            return method()
        return 0.0

    def __hash__(self):
        return id(self)


class TaskStart(GraphNode):
    is_start = True
    is_end = False

    def __init__(self, *argc, **argv):
        super().__init__(*argc, **argv)
        self._end = None

    @property
    def end(self):
        if self._end is None:
            raise Exception("No 'end node' associated to TaskStart.")
        return self._end()

    @property.setter('end')
    def set_end(self, end):
        if self._end is not None:
            raise Exception("Cannot associate 'end node' twice.")
        self._end = weakref.ref(end)


class TaskEnd(GraphNode):
    is_start = False
    is_end = True

    def __init__(self, *argc, **argv):
        super().__init__(*argc, **argv)
        self._start = None

    @property
    def start(self):
        if self._start is None:
            raise Exception("No 'start node' associated to TaskStart.")
        return self._start()

    @property.setter('start')
    def set_start(self, start):
        if self._start is not None:
            raise Exception("Cannot associate 'start node' twice.")
        self._start = weakref.ref(start)

    def get_pyority(self):
        return 0.0


class TaskNodePair:
    def __init__(self, start, end):
        assert start.data == end.data
        self.data = start.data
        start.end = end
        end.start = start
        self.start = start
        self.end = end
        self.subtasks = []

    def add_subtasks(self, *argc):
        self.subtasks.extend(argc)

    def __getitem__(self, key):
        return self.subtasks[key]
