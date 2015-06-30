About
-----
Smoker (aka Smoke Testing Framework) is a framework for distributed execution of Python modules, shell commands or external tools.
It executes configured plugins on request or periodically, unifies output and provide it via REST API for it's command-line or other client.

Also it's free software, licensed under the terms of BSD license - feel free to contribute!

Purpose and use
---------------
It was developed in GoodData to satisfy single use-case - be able to quickly and easily check that all services and components are functional overall cluster.
That may be simple if you have similar services with unified communication protocols. But if you have many services and components, written in many languages including Java, Perl, Erlang, Python together, you need more customizable approach, because each language has it's specific way to test things.

For example.. if you have services written in Java, you may use JMX interface to execute test function and get result.
For services with REST API, you may want to call it's API to get the result.
And of course you want to test system services. For example check Varnish backends health by executing `varnishadm 'debug.health'`. Or checking that Mongo is configured correctly by running custom Python plugin or shell script.

All those tests will return something different - you may get JSON response from REST API, XML from Java service, more complex data structure from Python plugin or simple STDOUT/STDERR and exit value from shell script. Smoker server will unify all those outputs and serve results over REST API so you can connect via CLI client and find out what is wrong in your cluster.

These tests may be executed periodically or when requested by client.
And actions are supported as well - you can write your own action plugin, parse result, decide and execute some action. For example, you can send status via NSCA to your Nagios system. Or you can just restart service when it's not working.

But Smoker can do more - you can use it if you want to execute any job and see it's result in a readable way. For some purposes, it may be more suitable than Cron.

Common use-cases in short:
 * execute smoke tests on newly deployed systems
 * execute checks periodically, send output to monitoring system (eg. Nagios)
 * execute jobs that requires attention on result or output (like Cron with ability to store results)
