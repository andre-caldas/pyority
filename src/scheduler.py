import numpy as np
from scipy.sparse import dok_array, identity

from nodes import TaskStart, TaskEnd, TaskNodePair


class Scheduler:
    _TaskStart = TaskStart
    _TaskEnd = TaskEnd

    def __init__(self, task_start=None, task_end=None):
        if task_start is not None:
            self._TaskStart = task_start
        if task_end is not None:
            self._TaskEnd = task_end
        self.graph = Graph()

    def add_task(self, task, *argc):
        pair = TaskNodePair(self._TaskStart(task), self._TaskEnd(task))
        self.graph.add_node(pair.start)
        self.graph.add_node(pair.end)
        self.graph.add_dependency(pair.end, pair.start)
        if argc:
            for n, task in enumerate(argc[0]):
                pair.add_subtasks(self.add_task(task, *(arg[n] for arg in argc[1:])))
        return pair

    def add_dependency(self, this, depends_on_this):
        if isinstance(this, TaskNodePair):
            this = this.start
        if isinstance(depends_on_this, TaskNodePair):
            depends_on_this = depends_on_this.end
        self.graph.add_dependency(this, depends_on_this)

    def __iter__(self):
        yield from self.graph


class Graph:
    def __init__(self):
        self._dirty = True
        self.idx_to_node = []
        self.node_to_idx = {}
        self.direct_dependencies = dok_array((128, 128), dtype=np.bool_)
        self.individual_pyorities = dok_array((128, 1), dtype=np.half)

    def prepare(self):
        if not self._dirty:
            return
        self._set_full_dependency_matrices()
        self._dirty = False

    @property
    def n_nodes(self):
        return len(self.idx_to_node)

    def add_node(self, node):
        self._dirty = True
        idx = len(self.idx_to_node)
        self.idx_to_node.append(node)
        self.node_to_idx[node] = idx
        assert len(self.node_to_idx) == len(self.idx_to_node)
        # Resize matrix if needed
        size = self.direct_dependencies.get_shape()[0]
        while size < self.n_nodes:
            size <<= 1
        self.direct_dependencies.resize(size, size)
        self.individual_pyorities.resize(size, 1)
        self.individual_pyorities[idx, 0] = node.pyority()

    def add_dependency(self, this, depends_on_this):
        self._dirty = True
        this_idx = self.node_to_idx[this]
        depends_idx = self.node_to_idx[depends_on_this]
        self.direct_dependencies[depends_idx, this_idx]

    def _set_full_dependency_matrices(self):
        self.direct_dependencies.resize(self.n_nodes, self.n_nodes)
        Id = identity(self.matrix_size, dtype=np.bool_)
        M = (self.direct_dependencies + Id).tocsr()
        nnz = 0
        next_nnz = M.nnz
        while nnz != next_nnz:
            M = M @ M
            nnz = next_nnz
            next_nnz = M.nnz
        self.full_dependency_rows = M

    def _set_full_pyorities(self):
        M = self.full_dependency_rows
        individual_pyorities = self.individual_pyorities.tocsc()
        # It seems scipy is optimized to deal with rows...
        self.full_pyorities = (M @ individual_pyorities).transpose().array()[0]
        fp_nnz_idx = [
            (-fp, M.getrow(i).nnz, i) for (i, fp) in enumerate(self.full_pyorities)
        ].sorted()
        self.order = [self.idx_to_node[fni[2]] for fni in fp_nnz_idx]

    def __iter__(self):
        self.prepare()
        yield from self.order
