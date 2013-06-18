# Smoker

Smoker (aka Smoke Testing Framework) is a framework for distributed execution of Python modules, shell commands or external tools.
It executes configured plugins on request or periodically, unifies output and provide it via REST API for it's command-line or other client.

Common use-cases:
 * execute smoke tests on newly deployed systems
 * execute checks periodically, send output to monitoring system (eg. Nagios)
 * execute jobs that requires attention on result or output (like Cron with ability to store results)

![Smoking catepillar](http://upload.wikimedia.org/wikipedia/commons/thumb/5/53/Alice_05a-1116x1492.jpg/672px-Alice_05a-1116x1492.jpg)

## Installation
With PIP:

	pip install -e 'git://github.com/gooddata/smoker.git#egg=smoker'

Or from local GIT checkout:

	python setup.py install

Then you can run it by init script or directly via smokerd.py

## Usage
### Smoker Daemon (smokerd)
Configuration can be done in two ways:

 * final configuration in single/multiple yaml files (if GENCONFIG option is 0)
 * generated configuration from directories (eg. for easier Puppet deploy) by init script

```
/etc/smokerd/
├── action.d
│   └── SendNSCA.yaml
├── common.yaml
├── plugin.d
│   ├── ConnectorZendesk3.yaml
│   ├── Uname.yaml
│   └── Uptime.yaml
├── smokerd.yaml
└── template.d
	├── BasePlugin.yaml
	└── JMXTest.yaml
```

#### Init script
Following options can be overwritten in /etc/default/smokerd

	PROG='smokerd'
	BINARY='/usr/bin/smokerd.py'
	PIDFILE='/var/run/smokerd.pid'
	LOCKFILE='/var/lock/subsys/smokerd'
	CONFDIR='/etc/smokerd'
	CONFIG="${CONFDIR}/smokerd.yaml"
	GENCONFIG=1
	SMOKERD_OPTIONS="-p ${PIDFILE} -v -c ${CONFIG}"

#### Manual start
Use following command to start smokerd in foreground with verbose output:

	/usr/bin/smokerd.py -c /etc/smokerd/smokerd.yaml -p /var/run/smokerd.pid -v -fg

##### Options
	usage: smokerd.py [-h] [-c CONFIG] [-p PIDFILE] [-fg] [--stop] [-v] [-d]

	optional arguments:
	  -h, --help            show this help message and exit
	  -c CONFIG, --config CONFIG
							Config file to use (default
							/etc/smokerd/smokerd.yaml)
	  -p PIDFILE, --pidfile PIDFILE
							PID file to use (default /var/run/smokerd.pid)
	  -fg, --foreground     Don't fork into background
	  --stop                Stop currently running daemon
	  -v, --verbose         Be verbose
	  -d, --debug           Debug output

### Smoker Client
Client side is tool that will connect to every smokerd server in cluster
It will collect and parse data from it and finally print human-readable result of overall cluster status.

See pydoc for smokercli.py or command-line help for latest informations:

	pydoc /usr/bin/smokercli.py
	/usr/bin/smokercli.py --help

#### Usage examples
	Show results on current host with minimal output
		smokercli.py -o minimal

	The same as above with normal output but force immediate run
		smokercli.py -f

	Force run of all plugins and print normal output for 2 specific nodes
		smokercli.py -f -s server1 server2

	Get results for plugins with category services, component apache
		smokercli.py --category services --component apache

	Get results for plugin Uname and Uptime and don't use colors
		smokercli.py -p Uname Uptime --no-colors

	Run only smoke tests (no health checks - you should always use --smoke or --health)
		smokercli.py --smoke -f

	Run again only smoke tests that failed
		smokercli.py --smoke --nook -f

	List plugins that are smoke tests and doesn't name selinux and rpm
		smokercli.py --smoke --exclude-plugins selinux rpm --list

	Exclude plugins of category workers
		smokercli.py --exclude --category services

### Plugin development
Plugins are usualy deployed in directory smoker/server/plugins but you can use whatever path that your Python interpreter use to search for modules.
Use pydoc and look at example plugins.

## License and credits
Smoker is a free software. It is released under the terms of BSD license (see LICENSE.TXT fore more informations).

Copyright (c) 2013, GoodData Corporation. All rights reserved.
