=======
AWS VPN
=======

This application is under development.

It provisions EC2 instances in AWS, and it costs **money**.

Use it at your own risk. You must know exactly what it does before you run this software.


Installation
------------

Requires ``boto``, ``fabric`` and a AWS account.

Make sure you copy the ``settings.cfg-dist`` to ``settings.cfg`` and add your details

I suggest you create a key pair only for this machine.


Provisioning the machine
------------------------

The machine can be provisioned by running::

    fab provision


Automatize the OSX connection
-----------------------------

There is a simple script provided that automatises the VPN connection, but it requires:

- An existing VPN with the credentials used for the VPN in the config file.
- The name of the VPN connection must be exactly the same as ``TAG_NAME`` in the fabric file ``proxy-aws``.

The script will automatically populate the URL of the VPN and connect.

Once the pre requisites are met the following command can be run::

    fab up


License
-------

Licensed under the MIT license.
