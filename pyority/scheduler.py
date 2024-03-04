import numpy as np
from scipy.sparse import dok_array, identity

from pyority.nodes import TaskStart, TaskEnd, TaskNodePair


class Graph:
    def __init__(self):
        self._dirty = True
        self.idx_to_node = []
        self.node_to_idx = {}
        self.direct_dependencies = dok_array((128, 128), dtype=np.bool_)
        self.individual_pyorities = dok_array((128, 1), dtype=np.half)
        self.full_dependency_rows = None
        self.full_dependency_cols = None

    def prepare(self):
        if not self._dirty:
            return
        self._set_full_dependency_matrices()
        self._set_full_pyorities()
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
        self.individual_pyorities.resize(1, size)
        self.individual_pyorities[0, idx] = node.pyority()

    def add_node_dependency(self, this, depends_on_this):
        assert this != depends_on_this
        self._dirty = True
        this_idx = self.node_to_idx[this]
        depends_idx = self.node_to_idx[depends_on_this]
        assert this_idx != depends_idx
        self.direct_dependencies[depends_idx, this_idx] = True

    def nodes_i_depend_on(self, node):
        col = self.direct_dependencies[:, [self.node_to_idx[node]]]
        return {self.idx_to_node[i] for i in col.nonzero()[0]}

    def nodes_i_fully_depend_on(self, node):
        idx = self.node_to_idx[node]
        col = self.full_dependency_cols[:, [idx]]
        return {self.idx_to_node[i] for i in col.nonzero()[0] if i != idx}

    def _set_full_dependency_matrices(self):
        self.direct_dependencies.resize(self.n_nodes, self.n_nodes)
        Id = identity(self.n_nodes, dtype=np.bool_)
        M = (self.direct_dependencies + Id).tocsr()
        nnz = 0
        next_nnz = M.nnz
        while nnz != next_nnz:
            M = M @ M
            nnz = next_nnz
            next_nnz = M.nnz
        self.full_dependency_rows = M.tocsr()
        self.full_dependency_cols = M.tocsc()

    def _set_full_pyorities(self):
        self.individual_pyorities.resize(1, self.n_nodes)
        MR = self.full_dependency_rows
        MC = self.full_dependency_cols
        individual_pyorities = self.individual_pyorities.tocsr()
        self.full_pyorities = (individual_pyorities @ MC).toarray()[0]
        fp_nnz_idx = sorted(
            (-fp, -MR[[i]].nnz, i) for (i, fp) in enumerate(self.full_pyorities)
        )
        self.order = [self.idx_to_node[fni[2]] for fni in fp_nnz_idx]

    def __iter__(self):
        self.prepare()
        yield from self.order


class Scheduler(Graph):
    _TaskStart = TaskStart
    _TaskEnd = TaskEnd

    def __init__(self, task_start=None, task_end=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if task_start is not None:
            self._TaskStart = task_start
        if task_end is not None:
            self._TaskEnd = task_end

    def add_task(self, task, *subtasks):
        pair = TaskNodePair(self._TaskStart(task), self._TaskEnd(task))
        self.add_node(pair.start)
        self.add_node(pair.end)
        self.add_node_dependency(pair.end, pair.start)
        if subtasks:
            self.add_subtasks(pair, *subtasks)
        return pair

    def add_subtasks(self, parent_pair, *subtasks):
        for task in subtasks:
            new_pair = self.add_task(task)
            self.add_node_dependency(new_pair.start, parent_pair.start)
            self.add_node_dependency(parent_pair.end, new_pair.end)
            parent_pair.register_subtask(new_pair)

    def add_task_dependency(self, this, depends_on_this):
        assert isinstance(this, TaskNodePair)
        assert isinstance(depends_on_this, TaskNodePair)
        self.add_node_dependency(this.start, depends_on_this.end)
