# -*- coding: utf-8 -*-
# Copyright © 2007-2013, All rights reserved. GoodData® Corporation, http://gooddata.com

__author__ = "miroslav.hedl@gooddata.com"
__maintainer__ = __author__


import re
import itertools
import collections
import string

################################################################################
##############################   dictionary  part   ############################
################################################################################
_tuple_cache = {}

def create(data, template, additional_fields=None):
    '''
    Converts nested dictionaries to list of named-tuples with fields
    taken from TEMPLATE.

    See included Yaml file for further details.
    :param dict data: dictionary of nested dictionaries/list
                      - fixed structure is presumed
    :param dict template: dictionary specifying matching fields
                          - useful to set from Yaml
    :param dict additional_fields: smart fields with string.template matching
                                   - can reference other fields from string
    :rtype: list of namedtuple
    :return: list of all fields captured from matching `data` against `template`

    >>> xs = iter_structure(..., ...,
    >>>          additional_fields={'NanaMeme':
    >>>                             "It was ${Name} ($occupation) ${date}"})
    >>> x = xs[0]
    >>> x.Name, x.occupation, x.date, x.NonExists
    'Queeg', 'mainframe', 'TODAY', None
    >>> x.NanaMeme
    'It was Queeg (mainframe) TODAY'
    '''

    m_regex = re.compile(r'''
     ^ \s*                                      # ignore initial whitespaces
     (?:
      (?: [$] (?P<bound> [_a-z] [0-9a-z_]*? ))  # match new bounded field name
      \s*
      (?:
       (?:   / (?P<re_bound> .* )     / )     | # but limit values by regular expression
       (?: - / (?P<re_bound_neg> .* ) / )       # but limit values by negation of regular expression
      )?                                      |
      (?:   / (?P<re> .* )     / )            | # limit values by regex
      (?: - / (?P<re_neg> .* ) / )            | # limit values by regex
      (?: [!] (?P<type> [_a-z] [0-9a-z_]*? )) | # limit values to instance of a type
      (?: \' (?P<literal> .*? [^ \'] ) \' )   | # only equals to this string literal
      (?P<normal> [^  \' $ !] .* )            | # only equals to this string literal
     )
     \s* $                                      # ignore ending whitespaces
     ''', flags=re.I | re.X)

    def m_eq(value, templ_value):
        '''
        Match value with defined template field.
        :param string value: value to match against template matcher
        :param string templ_value: template construct that limits possible values
        $Name       - will capture ANY value and add field to named tuple named 'Name'
        $Name/re/   - will capture ONLY values matching regex `re`, add field 'Name' with matched value
        $Name-/re/  - will capture ONLY values NOT matching regex `re`, add field 'Name' with matched value
        /re/        - will let through only values matching regex `re`, name is NOT bounded
        -/re/       - will let through only values NOT matching regex `re`, name is NOT bounded
        !Integral   - will only matches instances of given type (depends on :py:fn`m_get_type`
        literal     - will only pass values == literal
        '$weird_value' - if in single brackets, it's also literal, must be equal
        '''
        retMatch = None
        retBoundName = None
        m_t = m_regex.match(templ_value)
        if m_t:
            gd = m_t.groupdict()
            if gd.get('bound'):
                retBoundName = gd['bound']
                retMatch = True
            if gd.get('re_bound'):
                retMatch = re.match(gd['re_bound'], value)
            if gd.get('re'):
                retMatch = re.match(gd['re'], value)
            if gd.get('re_bound_neg'):
                retMatch = not re.match(gd['re_bound_neg'], value)
            if gd.get('re_neg'):
                retMatch = not re.match(gd['re_neg'], value)
            if gd.get('type'):
                retMatch = isinstance(value, m_get_type(gd['type']))
            if gd.get('literal'):
                retMatch = value == gd['literal']
            if gd.get('normal'):
                retMatch = value == gd['normal']
        return retMatch, retBoundName

    def iteritems(s):
        '''helper - takes/returns same things as enumerate(), for dict'''
        # return sorted(getattr(s, 'iteritems', s.items)())
        return getattr(s, 'iteritems', s.items)()

    def row_tuple(fields_str, additional_fields=None):
        '''
        Will return proper instance of namedtuple (all named Row).

        :param string fields_str: string of field names to conctruct named tuple from.
        For two same values of `fields_str`, you will always get the same type of namedtuple constructor (therefore isinstance works between fields combinations).
        :param dict additional_fiels: Row tuple will be extended to be asked on arbitrary value - defined in Yaml file. Value can reference other tuples's keys.
        :rtype: constructor for namedtuple defined by `fields_str`
        :return: constructor from cache or newly created one (added to cache right away)
        '''

        def mk__getattr__(additional_fields):
            """
            Extend attribute of `Row` namedtuple.
            Return `None` on invalid field.
            Return formatted string when name is in TEMPLATE dictionary.
            """
            def _attr_f(t, self, name):
                if t and name in t:
                    return string.Template(t[name]).safe_substitute(**self._asdict())
                return None
            return lambda self, name: _attr_f(additional_fields, self, name)

        if fields_str not in _tuple_cache:
            Row = collections.namedtuple('Row', fields_str)
            Row.__getattr__ = mk__getattr__(additional_fields=additional_fields)
            Row.__str = Row.__str__
            Row.__str__ = lambda t: (
                '|<| ' +
                ' | '.join('%s: %s' % (f, getattr(t, f)) for f in t._fields)
                + ' |>|')
            _tuple_cache[fields_str] = Row
        return _tuple_cache[fields_str]

    def is_iterable(s):
        '''Object is iterable but not string.'''
        return hasattr(s, '__iter__')

    def is_scalar(obj):
        '''Object is scalar / atom. Cannot be delved into.'''
        return not (isinstance(obj, collections.Mapping) or is_iterable(obj))

    def iter_tuplepairs(structure):
        '''
        Make sure dictionary and/or list iterate with same protocol.

        :rtype: iterator((value, value))
        :return: iterator of pairs [('key1', 'val1'), ('key1', 'val1'), ...]  or [(1, 'val1'), (2, 'val3')]
        '''
        # is some kind of dictionary
        if isinstance(structure, collections.Mapping):
            return iteritems(structure)
        # is some kind of enumarable, but NOT string
        elif isinstance(structure, collections.Sequence) or is_iterable(structure):
            return enumerate(structure)
        else:
            return tuple()

    def m_get_type(val):
        '''
        Integral type is only type that this function can verify.
        But it's okay, don't really need more types.

        :rval: bool
        :return: will check if `val` is instance of Integral
        '''
        ## or rather use eval() ?  ...later
        tp = ''.join(val.split('!'))
        if tp == 'Integral':
            import numbers
            return numbers.Integral
        return None

    def delve_in_template(templ, name, value):
        '''
        Step down the template dict to the proper sub-branch.
        '''
        if name is not None:
            return templ['$' + name]
        elif value in templ:
            return templ[value]
        types = itertools.ifilter(lambda x: x.startswith('!'),
                                  templ.iterkeys())
        for t in types:
            if isinstance(value, m_get_type(t)):
                return templ[t]
        raise IndexError("(VALUE: %s) or (PATTERN: %s) not in '%s'" % (value, name, templ))

    def m_field_dicts(data_fields, templ):
        '''
        Decision predicate if current captured fields satisfy matching rules and can delve further.

        :param dict data_fields: currently captured fields from input data-structure
        :param dict templ: template fields (for corresponding nested level)
        :rval: tuple (bool, list[(name, val))
        :return: Returns tuple with two elements. First - fields match; Second - list of name/value pairs
        '''
        def fields_only(d):
            '''
            :rval: dictionary
            "return: From input dict, return dict only with fields with atomic values
            '''
            flds = {}
            for field_candidate, value in d.iteritems():
                if is_scalar(value):
                    flds[field_candidate] = value
            return flds

        def satisfy_fields(d, t):
            retVal = tuple()
            template_fields = fields_only(t)
            plain_fields = list(itertools.ifilterfalse(lambda s: s.startswith('$'),
                                                       template_fields.iterkeys()))
            # make sure none of named template fields is missing
            if set(d.iterkeys()).issuperset(set(plain_fields)):
                for f in plain_fields:
                    match, bound_name = m_eq(d[f], t[f])

                    if not match:  # mismatch... skip this branch
                        return None, tuple()

                    if bound_name:
                        retVal = retVal + ((bound_name, d[f]),)
                return True, retVal
            return None, tuple()

        return satisfy_fields(data_fields, templ)

    def m_keyname(key, value, templ):
        def _match_names(name, templ):
            for pattern in templ.iterkeys():
                match, bound_name = m_eq(name, pattern)
                if match:
                    return match, bound_name
            return None, None

        state = []
        tv = templ.get(key)
        if is_scalar(value) or (tv is not None and is_scalar(tv)):
            state.append('field')
        else:
            state.append('nested')

        match, bound_key_name = _match_names(key, templ)
        if match:
            return state, bound_key_name
        return None, None

    def do_iter(path, container, t):
        children = []
        fields = {}

        for k, v in iter_tuplepairs(container):
            state, bound_key_name = m_keyname(k, v, t)
            if state is None:
                continue
            if 'field' in state:
                fields[k] = v
            if 'nested' in state:
                children.append((bound_key_name, k, v))

        match, bound_names = m_field_dicts(fields, t)
        if not match:
            return

        for (name, val, child) in children:
            sub_templ = delve_in_template(t, name, val)
            if isinstance(sub_templ, collections.Mapping):
                do_iter(path + bound_names + ((name, val),),
                        child,
                        sub_templ)
            elif is_iterable(sub_templ):
                for one_of_templ in sub_templ:
                    do_iter(path + bound_names + ((name, val),),
                            child,
                            one_of_templ)

        if len(children) == 0:
            processed.append(path + bound_names)

    processed = []
    do_iter(tuple(), data, template)
    rows = []
    for p in processed:
        traversed = zip(*filter(lambda t: t[0] is not None and t[1], p))
        fields = ' '.join(traversed[0])
        values = traversed[1]
        Row = row_tuple(fields, additional_fields=additional_fields)
        rows.append(Row(*values))
    return rows
