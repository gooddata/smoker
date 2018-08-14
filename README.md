<img src="http://upload.wikimedia.org/wikipedia/commons/thumb/5/53/Alice_05a-1116x1492.jpg/672px-Alice_05a-1116x1492.jpg" align=right width=340px />

- [Smoker](#smoker)
	- [Purpose and use](#purpose-and-use)
	- [Installation](#installation)
		- [Dependencies](#dependencies)
		- [Smoker](#smoker-1)
	- [Usage](#usage)
		- [Smoker Daemon (smokerd)](#smoker-daemon-smokerd)
			- [Init script](#init-script)
			- [Manual start](#manual-start)
	- [Example usage](#example-usage)
		- [Configuration](#configuration)
		- [Usage](#usage-1)
	- [Testing](#testing)
		- [Dependencies](#dependencies)
		- [Usage](#usage-2)
	- [Conclusion](#conclusion)

Smoker
======
Smoker (aka Smoke Testing Framework) is a framework for distributed execution of Python modules, shell commands or external tools.
It executes configured plugins on request or periodically, unifies output and provide it via REST API for it's command-line or other client.

In this document, I will describe it's purpose and use-cases more deeply as well as I will show some useful examples to give you some tips how you could use it.

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

Installation
------------
### Dependencies
Smoker is compatible and tested with Python 2.6.6 and newer.

To build smoker with 'make rpm' folowing packages required to be installed on the CentOS, RHEL or Fedora:

        yum install gcc rpm-build python-setproctitle python-flask-restful python2-setuptools

It doesn't have much dependencies, follow instructions bellow to install them:

With PIP:

	pip install psutil PyAML argparse simplejson setproctitle Flask-RESTful

Or install packages from your distribution repository.

### Smoker
With PIP (from Github):

	pip install -e 'git://github.com/gooddata/smoker.git#egg=smoker'

Or from Pypi (package is named gdc-smoker on Pypi):

	pip install gdc-smoker

Or from local GIT checkout:

	make install

This would invoke the setup.py script to perform the installation. You can also use the Makefile to build smoker RPM ($ make rpm).

Then you can run it by init script or directly via smokerd.py

Usage
-----
### Smoker Daemon (smokerd)
Configuration can be done in two different ways:

 * final configuration in single/multiple yaml files (if GENCONFIG option is 0, this is default), simply create `/etc/smokerd/smokerd.yaml`
 * generated configuration from directories (eg. for easier Puppet deploy) by init script (see structure bellow)

```
/etc/smokerd/
├── action.d
│   └── SendNSCA.yaml
├── common.yaml
├── plugin.d
│   ├── Apache.yaml
│   ├── Uname.yaml
│   └── Uptime.yaml
├── smokerd.yaml
└── template.d
	├── BasePlugin.yaml
	└── JMXTest.yaml
```

#### Init script
Distribution init script is written for RHEL and Debian, feel free to customize for your distribution and contribute.
Following options can be overwritten in `/etc/default/smokerd`

	PROG='smokerd'
	BINARY='/usr/bin/smokerd.py'
	PIDFILE='/var/run/smokerd.pid'
	LOCKFILE='/var/lock/subsys/smokerd'
	CONFDIR='/etc/smokerd'
	CONFIG="${CONFIGDIR}/smokerd.yaml"
	GENCONFIG=1
	SMOKERD_OPTIONS="-p ${PIDFILE} -v -c ${CONFIG}"

Simply copy script for your distribution into `/etc/init.d/smokerd`.
Smoker is using syslog for logging, so watch `/var/log/messages` if something is not working correctly.
You can change the logging configuration by creating `/etc/smokerd/logging.ini` using python's logging.config configuration dictionary schema.

##### Mac OS X
For Mac OS X, you can use org.smoker.smokerd.plist, just edit and fix path to smokerd.py binary or adjust for your needs. Don't forget to create configuration file in /etc/smokerd/smokerd.yaml before loading.

	sudo cp rc.d/init.d/org.smoker.smokerd.plist /Library/LaunchAgents/
	sudo launchctl load /Library/LaunchAgents/org.smoker.smokerd.plist

When Smoker is started this way, it doesn't log into syslog unless logging config file is in use.  Standard and error output goes into /var/log/smokerd-std*.log so watch it for more informations.

#### Manual start
Use following command to start smokerd in foreground with verbose output:

	/usr/bin/smokerd.py -v -fg

This is very good for testing and development purposees.

Example usage
-------------
Ok, now you have installed both daemon (smokerd) and console client (smokercli), let's go and configure some plugins..

### Configuration
Let's say we have multiple servers with similar setup, our simple configuration will look like this:

```
# Bind on all interfaces (ensure this port isn't accessible from outside world - Smokerd doesn't have authentication yet)
bind_host:   0.0.0.0
bind_port:   8086

pidfile:    /var/run/smokerd.pid

# You probably don't need these, because Smoker is using syslog
# but they can be handy during debugging of daemon startup,
# unhandled evil exceptions, etc.
stdin:      /dev/null
stdout:     /dev/null
stderr:     /dev/null

# Smoke test checks to run
plugins:
	## Jobs
	# Update our development project git repository every 60 seconds
    git-refresh:
        Interval:   60
        Category:   development
        Component:  myproject
        Command:    su karel -c 'cd /srv/www/myproject;git stash save;git pull --rebase'

	## Smoke tests
	# Check varnish backends health
	varnish:
		# Execute command and parse output by Python plugin
		Command: varnishadm 'debug.health'
		Parser: smoker.server.plugins.varnishparser
		# Don't run automatically
		Interval: 0
		# Just for categorization and filtering
		Category: infrastructure
		Component: varnish
		Type: smokeTest

	# Check mounted filesystems
	fsmount:
		# Use Python module, no Command or Parser
		Module: smoker.server.plugins.fsmount
		# Module can accept custom parameters, eg. to ignore all filesystems in /media dir
		Ignore: ^/media/.*$
		Interval: 0
		Category: system
		Component: filesystem
		Type: smokeTest

# Templates for plugins - this is good to easier configuration
templates:
    # Default template with options for all plugins
    BasePlugin:
		# It's always good to have default execution timeout
        Timeout:  30
        # History of results: no. of records to keep for each plugin
        History:  100
```

Good, now start smokerd with this configuration and let's see some usage examples and outputs.

### Usage
If you want to see last results on current host, simply run smokercli.py without parameters. This won't execute any plugins, just print last results and errors - to have output as short and useful as possible.
```
server1~# smokercli.py
server1                            [ERROR]
- fsmount                          [ERROR] (2014-01-17 16:12:58)
 -- /vpsadmin_backuper             [ERROR]
    [error] Read/Write: file write failed: [Errno 30] Read-only file system: '/vpsadmin_backuper/28640432-smoker.tmp'
- git-refresh                      [OK]
- varnish                          [UNKNOWN]
```

Now you want to see more details, so use `-o long` option to make output a little bit longer.
```
server1~# smokercli.py -o long
server1                            [ERROR]
- fsmount                          [ERROR] (2014-01-17 16:12:58)
 -- /vpsadmin_backuper             [ERROR]
    [info] Access: listed 2 items in directory
    [error] Read/Write: file write failed: [Errno 30] Read-only file system: '/vpsadmin_backuper/28640432-smoker.tmp'
- git-refresh                      [OK] (2014-01-17 16:19:48)
  [info] No local changes to save
  [info] Current branch master is up to date.
- Varnish                          [UNKNOWN]
```
You can also use more output types, check `smokercli.py --help` and don't fear to experiment.

Let's execute varnish plugin and check if it's working fine. We will use `-p varnish` option to work with only one plugin (but we can use multiple space-separated plugins) and `-f` option to force execution.
```
server1~# smokercli.py -o long -p Varnish -f
server1                            [WARN]
- varnish                          [WARN]
 -- www01                          [OK]
    [info] Response time: 0.010631
 -- www02                          [OK]
    [info] Response time: 0.01291
 -- www03-slow                     [WARN]
    [info] Response time: 1.523
```
That was a simple filter, you can filter by category (eg. `--category infrastructure`), component or type (smokeTest or healthCheck, eg. `--smoke` or `--health`). See help or PyDoc for more details.

Imagine you have multiple servers and you want to execute all smoke tests on them.
```
mgmt~# smokercli.py -s server1 server2 --smoke -f
server1                            [ERROR]
- fsmount                          [ERROR] (2014-01-17 16:12:58)
 -- /vpsadmin_backuper             [ERROR]
    [error] Read/Write: file write failed: [Errno 30] Read-only file system: '/vpsadmin_backuper/28640432-smoker.tmp'
- varnish                          [OK]

server2                            [OK]
- fsmount                          [OK] (2014-01-17 16:12:58)
- varnish                          [OK]
```

Ok, we have errors on some servers, we will log in, do some magic and want to execute only plugins that failed to see if it's ok now.
```
management~# smokercli.py -s server1 server2 --smoke --error -f
server1                            [OK]
- fsmount                          [OK] (2014-01-17 16:24:32)
```
Seems we have fixed the problem, so the same command will return nothing during next run, because we have no errored tests.
```
management~# smokercli.py -s server1 server2 --smoke --error -f
ERROR: No plugins found
```

Testing
-------------
If you want to make sure any change in Smoker won't affect your platform, you can run unittest on tests/server/test_*.py.
### Dependencies
Unit tests on smoker require py.test

With PIP:

	pip install pytest lockfile mock

### Usage
Run unit test file with command:

	py.test tests/server/test_*.py -vv

Or run all test files with command:

	py.test

pytest follows [standard test discovery](https://pytest.org/latest/goodpractices.html#conventions-for-python-test-discovery)

Conclusion
----------
Now you know how to simply setup and use Smoker.

To write custom plugins and parsers in Python, see example ones in `smoker/server/plugins` directory. For basic functionality, you can use shell scripts or commands without much coding and start using Smoker right now.

Enjoy and feel free to contribute!
