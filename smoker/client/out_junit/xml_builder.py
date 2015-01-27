# -*- coding: utf-8 -*-
# Copyright © 2007-2013, All rights reserved. GoodData® Corporation, http://gooddata.com

__author__ = "miroslav.hedl@gooddata.com"
__maintainer__ = __author__

# xml schema for jenkins junit xml format is here:
# https://svn.jenkins-ci.org/trunk/hudson/dtkit/dtkit-format/dtkit-junit-model/src/main/resources/com/thalesgroup/dtkit/junit/model/xsd/junit-4.xsd


import itertools
import collections
import string


################################################################################
##################################   xml  part   ###############################
################################################################################
class XmlBuilder(object):
    '''
    Template for building basic XML structure.

    Treat properties as xml elements, and kwargs like element attributes.

    :attribute _tag_name: holds tag name for given element instance
    :type tag_name:  string or None
    :attribute _children: holds tag name for given element
    :type _children: list of string or XmlBuilder instances
    :attribute _fields: embed all field names as attributes of xml element
                        (if field value is not None)
    :type _fields: list of tuples (pairs: field name, field value)
    :attribute _subst: if True, convert all bounded names to values;
                            leave template as-is otherwise
    :type _subst: bool
    :attribute _indent: fill beginning of lines with this string (repeat)
    :type _indent: str
    :attribute _crlf: for readabable xml leave as is (for compact xml, set :param:`indent` and :param:`crlf` to empty string)
    :type _crlf: str


    Examples:

    >>> xml = XmlBuilder('xml', subst=False)
    >>> xml.head.title <= "$title"
    >>> xml.color.rgb <= "$bg_color"
    >>> xml.body(id=123, bg_color="$bg_color") <= "I am ${name}!"
    >>> R, G, B = 15, 31, 63
    >>> print xml.dump(bg_color='${R:x}{G:x}{B:x}'.format(R=R, G=G, B=B), name='bingo', title="Simple Example")
    <xml>
      <head>
        <title>$title</title></head>
      <color>
        <rgb>$bg_color</rgb></color>
      <body bg_color="$bg_color" id="123">I am ${name}!</body></xml>

    >>> xml = XmlBuilder('xml')                   # subst=True is default
    >>> xml.head.title <= "$title"
    >>> xml.color.rgb <= "$bg_color"
    >>> xml.body(id=123, bg_color="$bg_color") <= "I am ${name}!"
    >>> R, G, B = 15, 31, 63
    >>> print xml.dump(bg_color='${R:x}{G:x}{B:x}'.format(R=R, G=G, B=B), name='dingo', title="Simple Example")
    <xml>
      <head>
        <title>Simple Example</title></head>
      <color>
        <rgb>$f1f3f</rgb></color>
      <body bg_color="$f1f3f" id="123">I am dingo!</body></xml>

    >>> nested = XmlBuilder('nested-struct')
    >>> (nested.first(name='$name 1', custom_dict={'system-out': "INFO MESSAGE..."})
     >>> <= XmlBuilder().nested(name='$name 2', custom_dict={'system-err': "ERROR MESSAGE..."})
     >>> <= XmlBuilder().other_nested(name='$name 3', custom_dict={'system-err': "ERROR MESSAGE..."})
     >>> <= XmlBuilder().yet_another_nested(name='$name 4', custom_dict={'system-err': "ERROR MESSAGE..."}))
    >>> print nested.dump(name='Case')
    <nested-struct>
      <first system-out="INFO MESSAGE..." name="Case 1">
        <nested system-err="ERROR MESSAGE..." name="Case 2">
          <other_nested system-err="ERROR MESSAGE..." name="Case 3">
            <yet_another_nested system-err="ERROR MESSAGE..." name="Case 4"></yet_another_nested></other_nested></nested></first></nested-struct>
    '''

    def __init__(self, tag_name=None, subst=True, indent='  ', crlf='\n'):
        '''
        Create new xml node.

        :param str? tag_name: If present, element has tag name and behaves normally
        :param bool subst: Do substitute unbounded names (in format '$name' or x-${Name}-y)
        :param str indent: Delimiter for indenting
        :param str crlf: Delimiter for line-breaks
        :rtype: XmlBuilder
        :return: instance that can be used as: callable, smart getattr, in with statement
        '''

        self._tag_name = tag_name
        self._children = []
        self._fields = []
        self._subst = subst
        self._indent = indent
        self._crlf = crlf

    ## special methods
    def __getattr__(self, tag_name):

        if tag_name.startswith('_'):
            return self.__dict__.get(tag_name)
        new = self.__class__(tag_name=tag_name,
                             subst=self._subst,
                             indent=self._indent,
                             crlf=self._crlf,
                             )
        self._children.append(new)
        return new

    def __setattr__(self, name, value):
        if name.startswith('_'):
            self.__dict__[name] = value
        else:
            self._fields.append((name, value))

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return False

    def __call__(self, custom_dict=None, **kwargs):
        '''
        Applies xml attributes to element.
        :param dict custom_dict: for values that not match python variables (like: 'system-err')
        :param dict kwargs: kwargs will override values in custom dict
        '''
        if custom_dict:
            for key, val in custom_dict.iteritems():
                self._fields.append((key, val))
        for key, val in kwargs.iteritems():
            self._fields.append((key, val))
        return self

    ## hidden helper methods
    def _sub(self, text, **kwargs):
        '''
        Evaluate text in environment of kwargs (do nothing if ..py:attr:`_subst` is False)
        '''
        if not self._subst:
            return text
        return string.Template(text).safe_substitute(**kwargs)

    def _open_tag(self, indent_lvl=0, **kwargs):
        '''
        Applies tuple fields (name, value) to xml.
        Both items must be not None to show in attribute list.
        '''
        return self._sub(
            self._crlf + "{i}<{name}".format(i=self._indent * indent_lvl,
                                             name=self._tag_name)
            + ''.join(' {name}="{val}"'.format(name=name, val=val)
                      for (name, val) in self._fields
                      if val is not None)
            + '>', **kwargs)

    def _close_tag(self, indent_lvl=0, **kwargs):
        '''Will close matching tag. Will nest to the right (better readability)'''
        return "</{name}>".format(name=self._tag_name)

    ## allows '<=' to add children
    def __le__(self, other):
        self._children.append(other)
        return self

    ## public methods
    def innerText(self, child):
        '''
        Will add text or another (arbitrary complex) XmlBuilder as children of element.
        '''
        self._children.append(child)
        return self

    def dump(self, indent_lvl=0, **kwargs):
        '''
        Recursively converts self and all children to xml.

        :param int indent_lvl: starting indentation level (less or eq then 0 is nothing)
        :param dict kwargs: provide means to influence value of unbounded template fields
        :rtype: string
        :return: formatted string in xml format
        '''
        dumped_children = []
        for child in itertools.ifilter(None, self._children):
            if isinstance(child, XmlBuilder):
                dumped_children.append(child.dump(indent_lvl=(indent_lvl + 1),
                                                  **kwargs))
            else:
                dumped_children.append("{child}".format(child=self._sub(child,
                                                                        **kwargs)))
        if self._tag_name:
            return (self._open_tag(indent_lvl, **kwargs)
                    + ''.join(dumped_children)
                    + self._close_tag(indent_lvl, **kwargs))
        return ''.join(dumped_children)
