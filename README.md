# Scheduler

When scheduling tasks,
the start of one might depend on the completion
of some other.

Pyority helps you to organize those *points in time*
(start or end of some task) in such a way that you can
iterate through them and populate them with information
without inconsistencies.


# Simple example

Suppose we have task A, with subtasks A0 and A1.
And A1 depends on A0.
And we have task B, with subtasks B0 and B1.
And B1 depends on B0.
And suppose that task B depends on completion of task A0.

```python
class MyTaskClass:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


A = MyTaksClass('A'), A0 = MyTaksClass('A0'), A1 = MyTaksClass('A1')
B = MyTaksClass('B'), B0 = MyTaksClass('B0'), B1 = MyTaksClass('B1')

scheduler = Scheduler()
a = scheduler.add_task(A, [A0, A1])
b = scheduler.add_task(B, [B0, B1])
scheduler.add_dependency(a[1], a[0])
scheduler.add_dependency(b[1], b[0])
scheduler.add_dependency(b, a[0])

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
Start A0
End   A0
Start B
Start B0
Start A1
End   B0
Start B1
End   A1
End   B1
End   A
End   B
```

Suppose your tasks know their time duration.
Then, following this order, you can place them in a timeline.
You decide when the project starts. This is the start of A.
It is also the start of A0.
Since you know duration, you know when A0 finishes.
Now, you know when B starts. You also know when B0 and A1 start.
And since you know duration, you know when B0 ends.
Now, you know when B1 starts.
At last, you know when A1 and B1 end.
And therefore, you know when A and B end.

We didn't have to follow the order `Start B`, `Start B0`, `Start A1`.
It could be `Start A1`, `Start B`, `Start B0`.
Or even `Start B`, `Start A1`, `Start B0`!!!
But `pyority` gives priority to nodes that have more stuff depending on them.
Depend on `Start A1`: `End A1` and `End A`.
Depend on `Start B`: `Start B0`, `Start B1`, `End B0`, `End B1` and `End B`.

Pyority will iterate through nodes in an order such that
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

When the *total pyority* of two nodes are equal,
we first iterate the one that has more nodes that depend
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
