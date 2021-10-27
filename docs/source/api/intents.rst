Intents
=======
Intents allow you to conditionally subscribe to pre-defined "intents",
groups of events defined by Discord. If you do not specify a certain intent,
you will not receive any of the gateway events that are batched into that group.
`Here <https://discord.com/developers/docs/topics/gateway#list-of-intents>`_ is a
list of intents and the discord intents they control.

.. autoclass:: cordy.models.intents.Intents
    :members:

Example
-------

.. code-block:: python3
    :caption: Example for enabling all intents

    cordy.Client(intents = cordy.Intents.all())


.. code-block:: python3
    :caption: Example of intents usage with client

    intents = cordy.Intents.default()
    intents.members = True
    intents.typing = False
    intents.dm_reactions = False
    cordy.Client(intents = intents)
