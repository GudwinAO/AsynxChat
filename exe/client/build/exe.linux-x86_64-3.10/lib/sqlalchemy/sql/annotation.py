# sql/annotation.py
# Copyright (C) 2005-2021 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""The :class:`.Annotated` class and related routines; creates hash-equivalent
copies of SQL constructs which contain context-specific markers and
associations.

"""

from . import operators
from .base import HasCacheKey
from .traversals import anon_map
from .visitors import InternalTraversal
from .. import util

EMPTY_ANNOTATIONS = util.immutabledict()


class SupportsAnnotations(object):
    _annotations = EMPTY_ANNOTATIONS

    @util.memoized_property
    def _annotations_cache_key(self):
        anon_map_ = anon_map()
        return (
            "_annotations",
            tuple(
                (
                    key,
                    value._gen_cache_key(anon_map_, [])
                    if isinstance(value, HasCacheKey)
                    else value,
                )
                for key, value in [
                    (key, self._annotations[key])
                    for key in sorted(self._annotations)
                ]
            ),
        )


class SupportsCloneAnnotations(SupportsAnnotations):

    _clone_annotations_traverse_internals = [
        ("_annotations", InternalTraversal.dp_annotations_key)
    ]

    def _annotate(self, values):
        """return a copy of this ClauseElement with annotations
        updated by the given dictionary.

        """
        new = self._clone()
        new._annotations = new._annotations.union(values)
        new.__dict__.pop("_annotations_cache_key", None)
        new.__dict__.pop("_generate_cache_key", None)
        return new

    def _with_annotations(self, values):
        """return a copy of this ClauseElement with annotations
        replaced by the given dictionary.

        """
        new = self._clone()
        new._annotations = util.immutabledict(values)
        new.__dict__.pop("_annotations_cache_key", None)
        new.__dict__.pop("_generate_cache_key", None)
        return new

    def _deannotate(self, values=None, clone=False):
        """return a copy of this :class:`_expression.ClauseElement`
        with annotations
        removed.

        :param values: optional tuple of individual values
         to remove.

        """
        if clone or self._annotations:
            # clone is used when we are also copying
            # the expression for a deep deannotation
            new = self._clone()
            new._annotations = util.immutabledict()
            new.__dict__.pop("_annotations_cache_key", None)
            return new
        else:
            return self


class SupportsWrappingAnnotations(SupportsAnnotations):
    def _annotate(self, values):
        """return a copy of this ClauseElement with annotations
        updated by the given dictionary.

        """
        return Annotated(self, values)

    def _with_annotations(self, values):
        """return a copy of this ClauseElement with annotations
        replaced by the given dictionary.

        """
        return Annotated(self, values)

    def _deannotate(self, values=None, clone=False):
        """return a copy of this :class:`_expression.ClauseElement`
        with annotations
        removed.

        :param values: optional tuple of individual values
         to remove.

        """
        if clone:
            s = self._clone()
            return s
        else:
            return self


class Annotated(object):
    """clones a SupportsAnnotated and applies an 'annotations' dictionary.

    Unlike regular clones, this clone also mimics __hash__() and
    __cmp__() of the original element so that it takes its place
    in hashed collections.

    A reference to the original element is maintained, for the important
    reason of keeping its hash value current.  When GC'ed, the
    hash value may be reused, causing conflicts.

    .. note::  The rationale for Annotated producing a brand new class,
       rather than placing the functionality directly within ClauseElement,
       is **performance**.  The __hash__() method is absent on plain
       ClauseElement which leads to significantly reduced function call
       overhead, as the use of sets and dictionaries against ClauseElement
       objects is prevalent, but most are not "annotated".

    """

    _is_column_operators = False

    def __new__(cls, *args):
        if not args:
            # clone constructor
            return object.__new__(cls)
        else:
            element, values = args
            # pull appropriate subclass from registry of annotated
            # classes
            try:
                cls = annotated_classes[element.__class__]
            except KeyError:
                cls = _new_annotation_type(element.__class__, cls)
            return object.__new__(cls)

    def __init__(self, element, values):
        self.__dict__ = element.__dict__.copy()
        self.__dict__.pop("_annotations_cache_key", None)
        self.__dict__.pop("_generate_cache_key", None)
        self.__element = element
        self._annotations = util.immutabledict(values)
        self._hash = hash(element)

    def _annotate(self, values):
        _values = self._annotations.union(values)
        return self._with_annotations(_values)

    def _with_annotations(self, values):
        clone = self.__class__.__new__(self.__class__)
        clone.__dict__ = self.__dict__.copy()
        clone.__dict__.pop("_annotations_cache_key", None)
        clone.__dict__.pop("_generate_cache_key", None)
        clone._annotations = values
        return clone

    def _deannotate(self, values=None, clone=True):
        if values is None:
            return self.__element
        else:
            return self._with_annotations(
                util.immutabledict(
                    {
                        key: value
                        for key, value in self._annotations.items()
                        if key not in values
                    }
                )
            )

    def _compiler_dispatch(self, visitor, **kw):
        return self.__element.__class__._compiler_dispatch(self, visitor, **kw)

    @property
    def _constructor(self):
        return self.__element._constructor

    def _clone(self):
        clone = self.__element._clone()
        if clone is self.__element:
            # detect immutable, don't change anything
            return self
        else:
            # update the clone with any changes that have occurred
            # to this object's __dict__.
            clone.__dict__.update(self.__dict__)
            return self.__class__(clone, self._annotations)

    def __reduce__(self):
        return self.__class__, (self.__element, self._annotations)

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        if self._is_column_operators:
            return self.__element.__class__.__eq__(self, other)
        else:
            return hash(other) == hash(self)

    @property
    def entity_namespace(self):
        if "entity_namespace" in self._annotations:
            return self._annotations["entity_namespace"].entity_namespace
        else:
            return self.__element.entity_namespace


# hard-generate Annotated subclasses.  this technique
# is used instead of on-the-fly types (i.e. type.__new__())
# so that the resulting objects are pickleable; additionally, other
# decisions can be made up front about the type of object being annotated
# just once per class rather than per-instance.
annotated_classes = {}


def _deep_annotate(element, annotations, exclude=None):
    """Deep copy the given ClauseElement, annotating each element
    with the given annotations dictionary.

    Elements within the exclude collection will be cloned but not annotated.

    """

    # annotated objects hack the __hash__() method so if we want to
    # uniquely process them we have to use id()

    cloned_ids = {}

    def clone(elem, **kw):
        id_ = id(elem)

        if id_ in cloned_ids:
            return cloned_ids[id_]

        if (
            exclude
            and hasattr(elem, "proxy_set")
            and elem.proxy_set.intersection(exclude)
        ):
            newelem = elem._clone()
        elif annotations != elem._annotations:
            newelem = elem._annotate(annotations)
        else:
            newelem = elem
        newelem._copy_internals(clone=clone)
        cloned_ids[id_] = newelem
        return newelem

    if element is not None:
        element = clone(element)
    clone = None  # remove gc cycles
    return element


def _deep_deannotate(element, values=None):
    """Deep copy the given element, removing annotations."""

    cloned = {}

    def clone(elem, **kw):
        if values:
            key = id(elem)
        else:
            key = elem

        if key not in cloned:
            newelem = elem._deannotate(values=values, clone=True)
            newelem._copy_internals(clone=clone)
            cloned[key] = newelem
            return newelem
        else:
            return cloned[key]

    if element is not None:
        element = clone(element)
    clone = None  # remove gc cycles
    return element


def _shallow_annotate(element, annotations):
    """Annotate the given ClauseElement and copy its internals so that
    internal objects refer to the new annotated object.

    Basically used to apply a "don't traverse" annotation to a
    selectable, without digging throughout the whole
    structure wasting time.
    """
    element = element._annotate(annotations)
    element._copy_internals()
    return element


def _new_annotation_type(cls, base_cls):
    if issubclass(cls, Annotated):
        return cls
    elif cls in annotated_classes:
        return annotated_classes[cls]

    for super_ in cls.__mro__:
        # check if an Annotated subclass more specific than
        # the given base_cls is already registered, such
        # as AnnotatedColumnElement.
        if super_ in annotated_classes:
            base_cls = annotated_classes[super_]
            break

    annotated_classes[cls] = anno_cls = type(
        "Annotated%s" % cls.__name__, (base_cls, cls), {}
    )
    globals()["Annotated%s" % cls.__name__] = anno_cls

    if "_traverse_internals" in cls.__dict__:
        anno_cls._traverse_internals = list(cls._traverse_internals) + [
            ("_annotations", InternalTraversal.dp_annotations_key)
        ]
    elif cls.__dict__.get("inherit_cache", False):
        anno_cls._traverse_internals = list(cls._traverse_internals) + [
            ("_annotations", InternalTraversal.dp_annotations_key)
        ]

    # some classes include this even if they have traverse_internals
    # e.g. BindParameter, add it if present.
    if cls.__dict__.get("inherit_cache", False):
        anno_cls.inherit_cache = True

    anno_cls._is_column_operators = issubclass(cls, operators.ColumnOperators)

    return anno_cls


def _prepare_annotations(target_hierarchy, base_cls):
    for cls in util.walk_subclasses(target_hierarchy):
        _new_annotation_type(cls, base_cls)
