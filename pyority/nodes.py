"""
 Nodes to represent what can have a dependency relation.

 The start of a task might depend on the completion of some other task.
 Therefore, the start and end of tasks are represented by nodes
 defined here.

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

import weakref


class GraphNode:
    """A node for the `Graph` class.

    The node is not useful by itself... you want some data associated to it.
    Your `data` object can have a `data.pyority()` method
    that will be used as this node's *pyority*.

    A GraphNode can also be used as a key in a dictionary, because it is *hashable*.
    Each instance is considered a different node.
    """

    def __init__(self, data):
        self.data = data

    def pyority(self):
        """Uses this node's data *pyority* if available.
        Otherwise, returns zero.
        """
        method = getattr(self.data, 'pyority', None)
        if method is not None:
            val = method()
            assert val >= 0
            return val
        return 0.0

    def __hash__(self):
        """Each instance is considered a different `GraphNode`."""
        return id(self)


class TaskStart(GraphNode):
    """Each task is associated to two types of node: `TaskStart` and `TaskEnd`.
    They are created in pairs and the *start* `node`
    knows its corresponing `node.end`.
    """
    is_start = True
    is_end = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._end = None

    @property
    def end(self):
        """Returns the associated *end node*."""
        if self._end is None:
            raise Exception("No 'end node' associated to TaskStart.")
        return self._end()

    @end.setter
    def end(self, end):
        """Sets the corresponging *end node*. This can be done only once."""
        if self._end is not None:
            raise Exception("Cannot associate 'end node' twice.")
        self._end = weakref.ref(end)

    def __str__(self):
        return f"Start: {self.data}"


class TaskEnd(GraphNode):
    """Each task is associated to two types of node: `TaskStart` and `TaskEnd`.
    They are created in pairs and the *end* `node`
    knows its corresponing `node.start`.
    """
    is_start = False
    is_end = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._start = None

    @property
    def start(self):
        """Returns the associated *end node*."""
        if self._start is None:
            raise Exception("No 'start node' associated to TaskStart.")
        return self._start()

    @start.setter
    def start(self, start):
        """Sets the corresponging *start node*. This can be done only once."""
        if self._start is not None:
            raise Exception("Cannot associate 'start node' twice.")
        self._start = weakref.ref(start)

    def pyority(self):
        return 0.0

    def __str__(self):
        return f"End  : {self.data}"


class TaskNodePair:
    """This is returned by `Schedule.add_task()`, and represents a pair of nodes.

    This class represents the task managed by `Schedule`.
    It is also aware of the subtasks added using `Schedule.add_subtasks()`.
    """

    def __init__(self, start, end):
        """Takes the `TaskStart` and `TaskEnd` instances that point to the same task
        and makes sure they point to each other.
        """
        assert start.data == end.data
        self.data = start.data
        start.end = end
        end.start = start
        self.start = start
        self.end = end
        self.subtasks = []

    def register_subtask(self, pair):
        """Internally keeps track of the subtasks.

        **Attention:** this does not add any dependencies to the `Scheduler`.
        """
        self.subtasks.append(pair)

    def register_subtasks(self, *args):
        """Internally keeps track of the subtasks.

        **Attention:** this does not add any dependencies to the `Scheduler`.
        """
        self.subtasks.extend(args)

    def __getitem__(self, key):
        """Allows one to access or iterate through the `TaskNodePair`s
        that correspond to this task's subtasks.
        Useage: `pair[2]`, to get the third subtask.
        """
        return self.subtasks[key]
