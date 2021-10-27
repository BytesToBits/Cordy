Runners
=======

.. automodule:: cordy.runner
    :members:

Example
-------

.. code-block:: python3
    :caption: Running a cordy client

    import cordy
    client = cordy.Client(token="<TOKEN>")

    cordy.run(client)

.. code-block:: python3
    :caption: Running multiple cordy clients

    import cordy

    tokens = ("<TOKENS>", ...)
    clients = [cordy.Client(token=token) for token in tokens]

    cordy.run_all(clients)
