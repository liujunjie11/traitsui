#------------------------------------------------------------------------------
#
#  Copyright (c) 2008, Enthought, Inc.
#  All rights reserved.
#
#  This software is provided without warranty under the terms of the BSD
#  license included in enthought/LICENSE.txt and may be redistributed only
#  under the conditions described in the aforementioned license.  The license
#  is also available online at http://www.enthought.com/licenses/BSD.txt
#
#  Thanks for using Enthought open source!
#
#  Author: David C. Morrill
#
#------------------------------------------------------------------------------
""" Defines the tuple editor factory for all traits user interface toolkits.
"""

#------------------------------------------------------------------------------
#  Imports:
#------------------------------------------------------------------------------

from __future__ import absolute_import

from traits.trait_base import SequenceTypes, enumerate

from traits.api import (
    Bool, Callable, HasTraits, List, BaseTuple, Unicode, Int, Any, TraitType)

# CIRCULAR IMPORT FIXME: Importing from the source rather than traits.ui.api
# to avoid circular imports, as this EditorFactory will be part of
# traits.ui.api as well.
from ..view import View

from ..group import Group

from ..item import Item

from ..editor_factory import EditorFactory

from ..editor import Editor


#------------------------------------------------------------------------------
#  'ToolkitEditorFactory' class:
#------------------------------------------------------------------------------

class ToolkitEditorFactory(EditorFactory):
    """ Editor factory for tuple editors.
    """
    #--------------------------------------------------------------------------
    #  Trait definitions:
    #--------------------------------------------------------------------------

    # Trait definitions for each tuple field
    types = Any

    # Labels for each of the tuple fields
    labels = List(Unicode)

    # Editors for each of the tuple fields:
    editors = List(EditorFactory)

    # Number of tuple fields or rows
    cols = Int(1)

    # Is user input set on every keystroke? This is applied to every field
    # of the tuple, provided the field does not already have an 'auto_set'
    # metadata or an editor defined.
    auto_set = Bool(True)

    # Is user input set when the Enter key is pressed? This is applied to
    # every field of the tuple, provided the field does not already have an
    # 'enter_set' metadata or an editor defined.
    enter_set = Bool(False)

    # The validation function to use for the Tuple. This will override the
    # validation function used when the editable Trait is a ValidatedTuple.
    validation = Callable


#------------------------------------------------------------------------------
#  'SimpleEditor' class:
#------------------------------------------------------------------------------

class SimpleEditor(Editor):
    """ Simple style of editor for tuples.

    The editor displays an editor for each of the fields in the tuple, based on
    the type of each field.
    """
    #--------------------------------------------------------------------------
    #  Finishes initializing the editor by creating the underlying toolkit
    #  widget:
    #--------------------------------------------------------------------------

    def init(self, parent):
        """ Finishes initializing the editor by creating the underlying toolkit
            widget.
        """
        self._ts = ts = TupleStructure(self)
        self._ui = ui = ts.view.ui(
            ts, parent, kind='subpanel').set(parent=self.ui)
        self.control = ui.control
        self.set_tooltip()

    #--------------------------------------------------------------------------
    #  Updates the editor when the object trait changes external to the editor:
    #--------------------------------------------------------------------------

    def update_editor(self):
        """ Updates the editor when the object trait changes external to the
            editor.
        """
        ts = self._ts

        for i, value in enumerate(self.value):
            setattr(ts, 'f{0}'.format(i), value)
            if ts.validation is not None:
                setattr(ts, 'invalid{0}'.format(i), False)

    #--------------------------------------------------------------------------
    #  Returns the editor's control for indicating error status:
    #--------------------------------------------------------------------------

    def get_error_control(self):
        """ Returns the editor's control for indicating error status.
        """
        return self._ui.get_error_controls()


#------------------------------------------------------------------------------
#  'TupleStructure' class:
#------------------------------------------------------------------------------

class TupleStructure (HasTraits):
    """ Creates a view containing items for each field in a tuple.
    """
    #--------------------------------------------------------------------------
    #  Trait definitions:
    #--------------------------------------------------------------------------

    # Editor this structure is linked to
    editor = Any

    # The constructed View for the tuple
    view = Any

    # Number of tuple fields
    fields = Int

    # The validation function to use for the Tuple.
    validation = Callable

    #--------------------------------------------------------------------------
    #  Initializes the object:
    #--------------------------------------------------------------------------

    def __init__(self, editor):
        """ Initializes the object.
        """
        factory = editor.factory
        types = factory.types
        labels = factory.labels
        editors = factory.editors
        cols = factory.cols
        validation = factory.validation

        # Save the reference to the editor:
        self.editor = editor

        # Get the tuple we are mirroring.
        object = editor.value

        # For each tuple field, add a trait with the appropriate trait
        # definition and default value:
        content = []
        self.fields = len(object)
        len_labels = len(labels)
        len_editors = len(editors)

        # Get global validation function.
        type = editor.value_trait.handler
        if hasattr(type, 'validation') and validation is None:
            self.validation = validation = type.validation

        # Get field types.
        if types is None:
            if isinstance(type, BaseTuple):
                types = type.types

        if not isinstance(types, SequenceTypes):
            types = [types]

        len_types = len(types)
        if len_types == 0:
            types = [Any]
            len_types = 1

        for i, value in enumerate(object):
            type = types[i % len_types]

            auto_set = enter_set = None
            # XXX: Should the trait auto_set and enter_set value override
            #      the user option defined in the factory?
            if isinstance(type, TraitType):
                auto_set = type.auto_set
                enter_set = type.enter_set
            if auto_set is None:
                auto_set = editor.factory.auto_set
            if enter_set is None:
                enter_set = editor.factory.enter_set

            label = ''
            if i < len_labels:
                label = labels[i]

            field_editor = None
            if i < len_editors:
                field_editor = editors[i]

            name = 'f{0}'.format(i)
            self.add_trait(name, type(
                value, event='field', auto_set=auto_set, enter_set=enter_set))
            if validation is not None:
                invalid = 'invalid{0}'.format(i)
                self.add_trait(invalid, Bool)
            else:
                invalid = ''

            item = Item(
                name, label=label, editor=field_editor, invalid=invalid)
            if cols <= 1:
                content.append(item)
            else:
                if (i % cols) == 0:
                    group = Group(orientation='horizontal')
                    content.append(group)

                group.content.append(item)

        self.view = View(Group(show_labels=(len_labels != 0), *content))

    #--------------------------------------------------------------------------
    #  Updates the underlying tuple when any field changes value:
    #--------------------------------------------------------------------------

    def _field_changed(self, name, old, new):
        """ Updates the underlying tuple when any field changes value.
        """
        editor = self.editor
        value = editor.value
        index = int(name[1:])
        value = self.editor.value
        if new != value[index]:
            new_value = tuple(
                getattr(self, 'f{0}'.format(i)) for i in range(self.fields))
            if self.validation is not None:
                if self.validation(new_value):
                    editor.value = new_value
                    for i in range(self.fields):
                        setattr(self, 'invalid{0}'.format(i), False)
                else:
                    setattr(self, 'invalid{0}'.format(index), True)
            else:
                editor.value = new_value


# Define the TupleEditor class.
TupleEditor = ToolkitEditorFactory
