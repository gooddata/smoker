# -*- coding: utf-8 -*-
# Copyright © 2007-2013, All rights reserved. GoodData® Corporation

__author__ = "miroslav.hedl@gooddata.com"
__maintainer__ = __author__


'''
Primary goal of this module is function `plugins_to_xml` that solves issue
PCI-1385.

This module converts plugins dictionary from `Smoker.py` and produces generic
list of named tuple based on configuration template (described inside).

Also implements simple but flexible
:py:class:`HtmlBuilder('node_name').sub_node(attr1='val1',
attr2='$GenericValue').innerText("Inside text...")`

Jenkins doesn't take structure of xUnit/jUnit XML file into account.
So sorting or structuring testsuites/testcases is futile effort.

Important is to properly set 'classname' and 'name' attributes for testcase
elements.
'''

from cgi import escape
import collections
import yaml

import default_config
import rows
from xml_builder import XmlBuilder


def plugins_to_xml(dict_data,
                   yaml_filename=None,
                   yaml_data=default_config.YAML_CONFIG,
                   dict_templates=['All'],
                   additional_fields='AdditionalFields',
                   ts_attr='HtmlTestSuiteAttr',
                   tc_attr='HtmlTestCaseAttr',
                   tc_elem='HtmlTestCaseElem'):
    """
    Provided data (from plugins dictionary) and walking template, get all valid
    items and convert it to jUnit xml representation.

    Function have sane defaults (depends on calee opinion):
    :param dict dict_data: datastructure taken as result from running smoke
                           tests (Smoker's output)
    :param str yaml_data: yaml string that will be taken as configuration; does
                          have precedence before `yaml_filename`
    :param str yaml_filename: if yaml_data is None, tries to read config from
                              file specified as path (relative from cwd)
    :param list dict_templates: TODO: probably remove this parameter
    :param dict additional_fields: get Yaml name for additional fields for Row
                                   namedtuple
    :param dict ts_attr: get Yaml name for configured testsuite xml attributes
    :param dict tc_attr: get Yaml name for configured testcase xml attributes
    :param dict tc_elem: get Yaml name for configured testcase xml subelements

    :rval: string
    :return: returns xml structure (testsuites corresponds to nodes, testcases
             to plugin)
    """
    def apply(inst, custom_dict=None, **kwargs):
        """
        Dynamically applies value of value as new value.

        >>> inst
        Row(node='stg-c3', plugin='alog', status='UNKNOWN')
        >>> inst.ClassName
        'stg-c3.alog'
        >>> custom_dict
        { 'name': 'node', 'classname': 'ClassName'}
        >>> apply(inst, custom_dict=custom_dict)
        { 'name': 'sgt-c3', 'classname': 'stg-c3.alog'}
        """
        applied_args = {}
        if custom_dict:
            for k, v in custom_dict.iteritems():
                applied_args[k] = getattr(inst, v)
        for k, v in kwargs.iteritems():
            applied_args[k] = getattr(inst, v)
        return applied_args

    if yaml_filename:
        with open(yaml_filename) as f:
            C = yaml.safe_load(f)
    else:
        C = yaml.safe_load(yaml_data)

    results = {}
    for template in dict_templates:
        results[template] = rows.create(data=dict_data,
                                        template=C[template],
                                        additional_fields=C[additional_fields])

    ts_data = {}
    for res in results.iterkeys():
        ts_data[res] = collections.defaultdict(list)
        ts_res = ts_data[res]
        for row in results[res]:
            ts_res[row.Node].append(row)

    junit_xml = XmlBuilder()
    for template_name, ts in sorted(ts_data.iteritems()):
        with junit_xml.testsuites as html_tss:
            html_tss(name=template_name)
            for node, tcs in sorted(ts.iteritems()):
                with html_tss.testsuite as html_ts:
                    first = tcs[0] if tcs else None
                    if first:
                        html_ts(custom_dict=apply(first,
                                                  custom_dict=C[ts_attr]))
                    for tc in sorted(tcs):
                        html_tc = html_ts.testcase(
                            custom_dict=apply(tc, custom_dict=C[tc_attr]))

                        if tc.CaseStatus == 'ERROR':
                            if tc.MsgError:
                                html_tc.error(message=escape(
                                    list_to_string(tc.MsgError), quote=1))
                            else:
                                html_tc.error()
                        elif tc.CaseStatus == 'WARN':
                            if tc.MsgWarn:
                                html_tc.failure(message=escape(
                                    list_to_string(tc.MsgWarn), quote=1))
                            else:
                                html_tc.failure()
    return junit_xml.dump()


def list_to_string(message):
    if isinstance(message, list):
        return '\n'.join(message)
    else:
        return message

# def test_onepass():
#     fixture_filename = 'tests/input_data_fixture'
#
#     with open('%s.yaml' % (fixture_filename,)) as f_in:
#         xml_txt = plugins_to_xml(yaml.safe_load(f_in))
#
#     with open('%s.testresult' % (fixture_filename,), 'w') as f_out:
#         f_out.write(xml_txt)
