####################################################
Testing performance of Ironic drivers for virtual HW
####################################################

Why doing that?
===============

Currently in OpenStack Ironic project [0] the main power and management driver
used with virtual hardware is SSH driver. It works by logging in to remote
host (hypervisor), executing there shell commands specific to a given
hypervisor type and parsing their output - all using pure Python SSH
implementation provided by ``Paramiko`` package.

In our opinion this is suboptimal due to many reasons, so we have proposed to
utilize ``Libvirt`` library and its Python interface provided by
``libvirt-python`` package to do the job (spec [1], Gerrit code review [2]).
Please read the spec for more rationale why we consider LIbVirt-based driver
would be a better option.
Below is a quick comparison of performance of these two implementations.

Testing setup
=============

Running tests on my laptop, connecting to a remote KVM host with 16GB of RAM
and quad-core Intel i5-3570 CPU.

On the host there are two DevStack VMs (4 vCPUs, 6 GB RAM each), plus 9 dummy
VMs which are only defined and not started. DevStack VMs are not executing
any considerable workload, just a usual DevStack idle churn.

Testing code is in ``test_ironic.py`` file in this repo. Code is run from
python virtualenv with dependencies installed from ``requirements.txt``,
versions of packages are taken from OpenStack global requirements [3]

Paramiko/Virsh related code is adapted almost verbatim from ssh module in
Ironic repo [4]. Libvirt related code is from the Gerrit review [2].

Running tests
=============

The most frequent (and time consuming) operation Ironic does with virtual
hardware is finding a particular VM on hypervisor by known MAC addresses
of its virtual NICs. We will test performance of exactly this procedure.

Tests are being run using Python's ``timeit`` module and its CLI.

Showing the actual list of VMs

::

  $ ssh pshchelokovskyy-pc "virsh list --all"
   Id    Name                           State
  ----------------------------------------------------
   2     heat                           running
   3     ironic                         running
   -     vm1                            shut off
   -     vm2                            shut off
   -     vm3                            shut off
   -     vm4                            shut off
   -     vm5                            shut off
   -     vm5-clone6                     shut off
   -     vm5-clone7                     shut off
   -     vm5-clone8                     shut off
   -     vm5-clone9                     shut off

Testing with MAC of first VM in returned list
---------------------------------------------

Testing Paramiko/Virsh driver
::

  python -m timeit -n 50 -s "from test_ironic import test" "test('virsh', '52:54:00:20:e1:dd')"
  50 loops, best of 3: 371 msec per loop

Testing LibVirt driver
::

  python -m timeit -n 50 -s "from test_ironic import test" "test('libvirt', '52:54:00:20:e1:dd')"
  50 loops, best of 3: 273 msec per loop


Testing with MAC of last VM in returned list
---------------------------------------------

Testing Paramiko/Virsh driver
::

  $ python -m timeit -n 50 -s "from test_ironic import test" "test('virsh', '52:54:00:73:8b:77')"
  50 loops, best of 3: 896 msec per loop

Testing LibVirt driver
::

  python -m timeit -n 50 -s "from test_ironic import test" "test('libvirt', '52:54:00:73:8b:77')"
  50 loops, best of 3: 289 msec per loop

Summary
=======

This simple testing suggests that even when hitting the first node in returned
list LibVirt driver is ~×1.3 faster than SSH one. The difference is even
bigger in case of hitting the last node (~×3), so on average in case of random
hits the **speed is improved about twice**. We suspect that for larger number
of VMs on hypervisor, improvement will scale up too.

References
==========

[0] http://docs.openstack.org/developer/ironic/

[1] https://review.openstack.org/#/c/254421/

[2] https://review.openstack.org/#/c/253096/

[3] https://github.com/openstack/requirements/blob/master/global-requirements.txt

[4] https://github.com/openstack/ironic/blob/master/ironic/drivers/modules/ssh.py
