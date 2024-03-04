"""
 Where the Scheduler class is defined.

 LICENSE

 Copyright (c) 2024 André Caldas de Souza <andre.em.caldas@gmail.com>

 This file is part of Pyority, a software allows you to attribute
 data, like duration or resource allocation, to tasks
 in a consistent way to generate something that could be presented,
 for example in a Gnatt Chart.

 Pyority is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 Pyority is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with OpenShot Library.  If not, see <http://www.gnu.org/licenses/>.
"""

import numpy as np
from scipy.sparse import dok_array, identity

from pyority.nodes import TaskStart, TaskEnd, TaskNodePair


class Graph:
    """A graph of nodes, representing their dependency relation.

    Probably you want to use the derived `Scheduler` class, instead.

    At the end of the day, what we have is a bunch of nodes
    that point to (or from, if you like) nodes that directly
    depend on it.  This class takes those relations and produce
    a symmetric transitive closure of it.  That is, if node `C`
    depends on node `B` and node `B` depends on `A`, having the
    transitive closure allows one to readly state that node `C`
    depends on node `A`.  We assume there are no cycles in the graph.
    But things shall not break if there are.

    Having computed the transitive closure, we use it and also the
    *pyority* of each node, to traverse them in a consistent fashion.

    We use the term *full* to talk about data that refers
    to the transitive colsure.  But we shall say that `C` depends on `A`
    to mean dependency that might be direct or indirect.
    To talk exclusivelly about direct dependencies,
    we shall use the qualifier: *direct* dependency.
    A *direct* dependency is an explicitely stated dependency,
    using `Graph.add_node_dependency()`.
    """

    def __init__(self):
        self._dirty = True
        self.idx_to_node = []
        self.node_to_idx = {}
        self.direct_dependencies = dok_array((128, 128), dtype=np.bool_)
        self.individual_pyorities = dok_array((128, 1), dtype=np.half)
        self.full_dependency_rows = None
        self.full_dependency_cols = None

    def prepare(self):
        """Makes sure the computed data is up to date."""
        if not self._dirty:
            return
        self._set_full_dependency_matrices()
        self._set_full_pyorities()
        self._dirty = False

    @property
    def n_nodes(self):
        """Number of nodes in this graph."""
        return len(self.idx_to_node)

    def add_node(self, node):
        """Adds a new node to the graph."""
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

    def add_node_dependency(self, this, depends_on_that):
        """Imposes that `this` node `depends_on_that` node."""
        assert this != depends_on_that
        self._dirty = True
        this_idx = self.node_to_idx[this]
        depends_idx = self.node_to_idx[depends_on_that]
        assert this_idx != depends_idx
        self.direct_dependencies[depends_idx, this_idx] = True

    def nodes_i_depend_on(self, node):
        """The set of nodes `node` **directly** depends on."""
        col = self.direct_dependencies[:, [self.node_to_idx[node]]]
        return {self.idx_to_node[i] for i in col.nonzero()[0]}

    def nodes_i_fully_depend_on(self, node):
        """The set of nodes `node` depends on. Directly or not."""
        idx = self.node_to_idx[node]
        col = self.full_dependency_cols[:, [idx]]
        return {self.idx_to_node[i] for i in col.nonzero()[0] if i != idx}

    def _set_full_dependency_matrices(self):
        """Computes the xxxx."""
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
        """Precomputes the *full pyority*.
        That is, it associates to each node the sum of its *pyority*
        and the *pyorities* for all nodes that depend on it.
        """
        self.individual_pyorities.resize(1, self.n_nodes)
        MR = self.full_dependency_rows
        MC = self.full_dependency_cols
        individual_pyorities = self.individual_pyorities.tocsr()
        assert all(
            self.individual_pyorities[i, j] >= 0.0
            for i, j in zip(*self.individual_pyorities.nonzero())
        )
        self.full_pyorities = (individual_pyorities @ MC).toarray()[0]
        fp_nnz_idx = sorted(
            (-fp, -MR[[i]].nnz, i) for (i, fp) in enumerate(self.full_pyorities)
        )
        self.order = [self.idx_to_node[fni[2]] for fni in fp_nnz_idx]

    def __iter__(self):
        """Iterates through all nodes in a way consistent with their dependencies.
        This also takes into account the *full pyority* of a node.
        Nodes with greater *full pyority* are iterated first.
        """
        self.prepare()
        yield from self.order


class Scheduler(Graph):
    """Higher level interface to Graph with methods to handle task dependencies."""

    _TaskStart = TaskStart
    _TaskEnd = TaskEnd

    def __init__(self, task_start=None, task_end=None):
        """You can implement your own classes for the start and end nodes."""
        super().__init__()
        if task_start is not None:
            self._TaskStart = task_start
        if task_end is not None:
            self._TaskEnd = task_end

    def add_task(self, task, *subtasks):
        """A task has two nodes (*start* and *end*).
        To finish a task one needs to begin. So, *end* depends on *start*.

        As a shortcut `to add_subtasks()`,
        one can also list subtasks of this task.
        Those two are the same:
            ```
            pair = scheduler.add_task(task, sub1, sub2, sub3)
            # And...
            pair = scheduler.add_task(task)
            scheduler.add_subtasks(pair, sub1, sub2, sub3)
            ```
        """
        pair = TaskNodePair(self._TaskStart(task), self._TaskEnd(task))
        self.add_node(pair.start)
        self.add_node(pair.end)
        self.add_node_dependency(pair.end, pair.start)
        if subtasks:
            self.add_subtasks(pair, *subtasks)
        return pair

    def add_subtasks(self, parent_pair, *subtasks):
        """A subtask is a pair of nodes whose *start* depends on its parent's *start*;
        and such that the parent's *end* depends on the subtask's *end*."""
        for task in subtasks:
            new_pair = self.add_task(task)
            self.add_node_dependency(new_pair.start, parent_pair.start)
            self.add_node_dependency(parent_pair.end, new_pair.end)
            parent_pair.register_subtask(new_pair)

    def add_task_dependency(self, this, depends_on_that):
        """The *start* of `this` `depends_on_that`'s *end*."""
        assert isinstance(this, TaskNodePair)
        assert isinstance(depends_on_that, TaskNodePair)
        self.add_node_dependency(this.start, depends_on_that.end)
