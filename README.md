# Scheduler

When scheduling tasks,
the start of one might depend on the completion
of some other.

Pyority helps you to organize those *points in time*
(start or end of some task) in such a way that you can
iterate through them and populate them with information
in a way consistent with their execution timeline.


# Simple example

Suppose we have task A, with subtasks A1 and A2.
And A2 depends on A1.
And we have task B, with subtasks B1 and B2.
And B2 depends on B1.
And suppose that task B depends on completion of task A1.

```python
class MyTaskClass:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


A = MyTaksClass('A'), A1 = MyTaksClass('A1'), A2 = MyTaksClass('A2')
B = MyTaksClass('B'), B1 = MyTaksClass('B1'), B2 = MyTaksClass('B2')

scheduler = Scheduler()
a, a1, a2 = scheduler.add_tasks(A, [A1, A2])
b, b1, b2 = scheduler.add_tasks(B, [B1, B2])
scheduler.add_dependency(a2, a1)
scheduler.add_dependency(b2, b1)
scheduler.add_dependency(b, a1)

for node in scheduler:
    if node.is_start:
        print(f"Start {node.get_data()}.")
    else:
        print(f"End   {node.get_data()}.")
```

A possible output:

```console
$ python3 schedule.py
Start A
Start A1
End   A1
Start B
Start B1
Start A2
End B1
Start B2
End A2
End B2
End A
End B
```

Suppose your tasks know their time duration.
Then, following this order, you can place them in a timeline.
You decide when the project starts. This is the start of A.
It is also the start of A1.
Since you know duration, you know when A1 finishes.
Now, you know when B starts. You also know when B1 and A2 start.
And since you know duration, you know when B1 ends.
Now, you know when B2 starts.
At last, you know when A2 and B2 end.
And therefore, you know when A and B end.

We didn't have to follow the order `Start B`, `Start B1`, `Start A2`.
It could be `Start A2`, `Start B`, `Start B1`.
Or even `Start B`, `Start A2`, `Start B1`!!!
But `pyority` gives priority to nodes that have more stuff depending on them.
Depend on `Start A2`: `End A2` and `End A`.
Depend on `Start B`: `Start B1`, `Start B2`, `End B1`, `End B2` and `End B`.

Pyority will iterate through nodes in such an order that
you can populate the data in a consistent way.
Notice that the iteration order `End A` and `End B` does not mean that
task A needs to finish before task B.
It is just that it is safe to determine a date for `End A`
and then determine a date for `End B`.
For this specific case,
the end of A and B can be specified in any order,
and pyority chooses one of the possibilities.


# Giving pyorities to tasks

Some tasks should have a *priority* and be iterated earlier, if possible.
It is not exactly a "priority" in the sense that this task is more important.
It could be, for example, the estimated task duration.
We call the choosen quantity a *pyority*.
The *total pyority* for a task is the sum of its *pyority* and
the *pyority* of all tasks that depend on it.

When the *total pyority* of two tasks are equal,
we first iterate the node that has more nodes that depend
(directly or indirectly) on it.
If they have the same dependent node count,
the order is not specified and is implementation dependent.

There are basically two ways to define a task's *piority*.

## Define a `pyority` method in `MyTaskClass`

The default is that if you define `MyTaskClass.pyority()`
returning a number, the returned value will be this task's *pyority*.

```python
class MyTaskClass:
    def __init__(self, name, duration):
        self.name = name
        self.duration = duration

    def pyority(self):
        return self.duration
```

There are two types of task nodes: `TaskStart` and `TaskEnd`.
The default is that `TaskStart.pyority()` returns the result of calling
your classe's `pyority()` method.
And `TaskEnd.pyority()` simply returns zero.

This way, the *total pyority*  calculated for a task start
is the value returned by your classe's `pyority()` plus the *pyority*
of all nodes that depend (directly or indirectly) on the start of this task.
On the other hand, the *total pyority* for a task end
is simply the sum of the *pyorities* of the nodes that depend
(directly or indirectly) on the completion of this task.


## Subclass `TaskStart.pyority()` (and/or `TaskEnd.pyority()`)

I think you probably do not want to change `TaskEnd`.
Here is an example.

```python
class MyTaskStart(TaskStart):
    def pyority(self):
        return self.get_data().duration

scheduler = Scheduler(task_start=MyTaskStart)
```
