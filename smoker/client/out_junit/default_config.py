# -*- coding: utf-8 -*-
# Copyright © 2007-2018, All rights reserved. GoodData® Corporation, http://gooddata.com

YAML_CONFIG = \
'''
AdditionalFields:
  ClassName:
    ${Node}.${Plugin}
  TestSuiteName:
    node $Node
  TestCaseName:
    plugin $Plugin
  ErrorMessage:
    Smoker plugin failed. See STD-ERR for more details.


HtmlTestSuiteAttr:
  errors: _count
  failures: _count
  tests: _count
  name: TestSuiteName
  hostname: Node
  id: UNUSED
  package: UNUSED
  timestamp: LastRun


# this is ignored and hard-coded
#
# HtmlTestCaseElem:
#   system-out: MsgInfo
#   system-err: MsgWarn

HtmlTestCaseAttr:
  classname: ClassName
  name: CaseName
  status: CaseStatus


All:
  '$Node':
    plugins:
      '$Plugin':
        lastResult:
          status: '$PluginStatus /ERROR|WARN|OK/'
          lastRun: '$LastRun'
          messages:
            info:  '$MsgInfo'
            warn:  '$MsgWarn'
            error:  '$MsgError'
          componentResults:
            '!Integral':
             componentResult:
              messages:
                info:  '$MsgInfo'
                warn:  '$MsgWarn'
                error:  '$MsgError'
              name:   '$CaseName'
              status: '$CaseStatus'
'''
