Filter Scheduler
================

The **Filter Scheduler** supports `filtering` zun compute hosts to make
decisions on where a new container should be created.

Filtering
---------

Filter Scheduler iterates over all found compute hosts,evaluating each host
against a set of filters. The Scheduler then chooses a host for the requested
container. A specific filter can decide whether to pass or filter out a
specific host. The decision is made based on the user request specification,
the state of the host, and/or some extra information.

If the Scheduler cannot find candidates for the container, it means that
there are no appropriate host where that container can be scheduled.

The Filter Scheduler has a set of ``filters`` that are built-in. If the
built-in filters are insufficient, you can implement your own filters with your
filtering algorithm.

There are many standard filter classes which may be used
(:mod:`zun.scheduler.filters`):

* CPUFilter - filters based on CPU core utilization. It passes hosts with
  sufficient number of CPU cores.
* RamFilter - filters hosts by their RAM. Only hosts with sufficient RAM
  to host the instance are passed.
* LabelFilter - filters hosts based on whether host has the CLI specified
  labels.
* ComputeFilter - filters hosts that are operational and enabled. In general,
  you should always enable this filter.
* RuntimeFilter - filters hosts by their runtime. It passes hosts with
  the specified runtime.

Configuring Filters
-------------------

To use filters you specify two settings:

* ``filter_scheduler.available_filters`` - Defines filter classes made
  available to the scheduler.
* ``filter_scheduler.enabled_filters`` - Of the available filters, defines
  those that the scheduler uses by default.

The default values for these settings in zun.conf are:

::

    --filter_scheduler.available_filters=zun.scheduler.filters.all_filters
    --filter_scheduler.enabled_filters=RamFilter,CPUFilter,ComputeFilter,RuntimeFilter

With this configuration, all filters in ``zun.scheduler.filters``
would be available, and by default the RamFilter and CPUFilter would be
used.

Writing Your Own Filter
-----------------------

To create **your own filter** you must inherit from
BaseHostFilter and implement one method:
``host_passes``. This method should return ``True`` if the host passes the
filter.

P.S.: you can find more examples of using Filter Scheduler and standard filters
in :mod:`zun.tests.scheduler`.
