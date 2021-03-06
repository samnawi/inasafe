# coding=utf-8
"""InaSAFE Wizard Step Field."""

import re

from PyQt4 import QtCore
from PyQt4.QtGui import QListWidgetItem, QAbstractItemView

from safe.utilities.i18n import tr
from safe import messaging as m

from safe.definitions.layer_purposes import (
    layer_purpose_aggregation, layer_purpose_hazard, layer_purpose_exposure)
from safe.definitions.layer_modes import layer_mode_continuous
from safe.gui.tools.wizard.wizard_step import (
    WizardStep, get_wizard_step_ui_class)
from safe.gui.tools.wizard.wizard_strings import (
    field_question_subcategory_unit,
    field_question_subcategory_classified,
    field_question_aggregation)
from safe.gui.tools.wizard.utilities import (
    get_question_text, skip_inasafe_field)
from safe.definitions.utilities import (
    get_fields, get_non_compulsory_fields, get_field_groups)
from safe.definitions.fields import population_count_field

__copyright__ = "Copyright 2016, The InaSAFE Project"
__license__ = "GPL version 3"
__email__ = "info@inasafe.org"
__revision__ = '$Format:%H$'

FORM_CLASS = get_wizard_step_ui_class(__file__)

# Mode
SINGLE_MODE = 'single'
MULTI_MODE = 'multi'


class StepKwField(WizardStep, FORM_CLASS):

    """InaSAFE Wizard Step Field."""

    def __init__(self, parent=None):
        """Constructor for the tab.

        :param parent: widget to use as parent (Wizard Dialog).
        :type parent: QWidget
        """
        WizardStep.__init__(self, parent)
        self.mode = SINGLE_MODE

    def is_ready_to_next_step(self):
        """Check if the step is complete.

        If so, there is no reason to block the Next button.

        :returns: True if new step may be enabled.
        :rtype: bool
        """
        # Choose hazard / exposure / aggregation field is mandatory
        return bool(self.selected_fields())

    def get_next_step(self):
        """Find the proper step when user clicks the Next button.

        :returns: The step to be switched to
        :rtype: WizardStep
        """
        layer_purpose = self.parent.step_kw_purpose.selected_purpose()
        if layer_purpose != layer_purpose_aggregation:
            subcategory = self.parent.step_kw_subcategory.\
                selected_subcategory()
        else:
            subcategory = {'key': None}

        # Has layer groups, go to field mapping
        field_groups = get_field_groups(
            layer_purpose['key'], subcategory['key'])
        if field_groups:
            return self.parent.step_kw_fields_mapping

        # Has classifications, go to multi classifications
        if subcategory.get('classifications'):
            if layer_purpose == layer_purpose_hazard:
                return self.parent.step_kw_multi_classifications
            elif layer_purpose == layer_purpose_exposure:
                return self.parent.step_kw_classification

        # Check if it can go to inasafe field step
        non_compulsory_fields = get_non_compulsory_fields(
            layer_purpose['key'], subcategory['key'])
        if not skip_inasafe_field(self.parent.layer, non_compulsory_fields):
            return self.parent.step_kw_inasafe_fields

        # Check if it can go to inasafe default field step
        default_inasafe_fields = get_fields(
            layer_purpose['key'],
            subcategory['key'],
            replace_null=True,
            in_group=False)
        if default_inasafe_fields:
            return self.parent.step_kw_default_inasafe_fields

        # Any other case
        return self.parent.step_kw_source

    # noinspection PyPep8Naming
    def on_lstFields_itemSelectionChanged(self):
        """Update field_names description label and unlock the Next button.

        .. note:: This is an automatic Qt slot
           executed when the field_names selection changes.
        """
        self.clear_further_steps()
        field_names = self.selected_fields()
        layer_purpose = self.parent.step_kw_purpose.selected_purpose()
        # Exit if no selection
        if not field_names:
            self.parent.pbnNext.setEnabled(False)
            self.lblDescribeField.setText('')
            return
        # Compulsory fields can be list of field name or single field name.
        # We need to iterate through all of them
        if not isinstance(field_names, list):
            field_names = [field_names]
        field_descriptions = ''
        feature_count = self.parent.layer.featureCount()
        for field_name in field_names:
            layer_fields = self.parent.layer.dataProvider().fields()
            field_index = layer_fields.indexFromName(field_name)
            # Exit if the selected field_names comes from a previous wizard run
            if field_index < 0:
                return

            # Generate description for the field.
            field_type = layer_fields.field(field_name).typeName()
            field_index = layer_fields.indexFromName(field_name)
            unique_values = self.parent.layer.uniqueValues(field_index)
            unique_values_str = [
                i is not None and unicode(i) or 'NULL'
                for i in unique_values[0:48]]
            unique_values_str = ', '.join(unique_values_str)
            field_descriptions += tr('<b>Field name</b>: {field_name}').format(
                field_name=field_name)
            field_descriptions += tr(
                '<br><b>Field type</b>: {field_type}').format(
                field_type=field_type)
            if (feature_count != -1 and (
                        layer_purpose == layer_purpose_aggregation)):
                if len(unique_values) == feature_count:
                    unique = tr('Yes')
                else:
                    unique = tr('No')
                field_descriptions += tr(
                    '<br><b>Unique</b>: {unique} ({unique_values_count} '
                    'unique values from {feature_count} features)'.format(
                        unique=unique,
                        unique_values_count=len(unique_values),
                        feature_count=feature_count))
            field_descriptions += tr(
                '<br><b>Unique values</b>: {unique_values_str}<br><br>'
            ).format(unique_values_str=unique_values_str)

        self.lblDescribeField.setText(field_descriptions)

        self.parent.pbnNext.setEnabled(True)

    def selected_fields(self):
        """Obtain the fields selected by user.

        :returns: Keyword of the selected field.
        :rtype: list, str
        """
        items = self.lstFields.selectedItems()
        if items and self.mode == MULTI_MODE:
            return [item.text() for item in items]
        elif items and self.mode == SINGLE_MODE:
            return items[0].text()
        else:
            return []

    def clear_further_steps(self):
        """Clear all further steps to re-init widget."""
        self.parent.step_kw_classify.treeClasses.clear()

    def set_widgets(self):
        """Set widgets on the Field tab."""
        self.clear_further_steps()
        purpose = self.parent.step_kw_purpose.selected_purpose()
        subcategory = self.parent.step_kw_subcategory.selected_subcategory()
        unit = self.parent.step_kw_unit.selected_unit()

        # Set mode
        # Notes(IS) I hard coded this one, need to fix it after it's working.
        if (self.parent.field_keyword_for_the_layer() ==
                population_count_field['key']):
            self.mode = MULTI_MODE
        else:
            self.mode = SINGLE_MODE

        if purpose == layer_purpose_aggregation:
            question_text = field_question_aggregation
        elif self.parent.step_kw_layermode.\
                selected_layermode() == layer_mode_continuous and unit:
            subcategory_unit_relation = get_question_text(
                '%s_%s_question' % (subcategory['key'], unit['key']))
            if 'MISSING' in subcategory_unit_relation:
                subcategory_unit_relation = self.tr(
                    '{subcategory} in {unit} unit').format(
                    subcategory=subcategory['name'].lower(),
                    unit=unit['plural_name'])
            question_text = field_question_subcategory_unit % (
                purpose['name'],
                subcategory['name'],
                unit['name'],
                subcategory_unit_relation)
        else:
            question_text = field_question_subcategory_classified % (
                subcategory['name'])
        if self.mode == SINGLE_MODE:
            question_text += tr('\nYou can select 1 field only.')
            self.lstFields.setSelectionMode(QAbstractItemView.SingleSelection)
        elif self.mode == MULTI_MODE:
            question_text += tr(
                '\nYou can select more than 1 field. InaSAFE will sum up the '
                'value of the fields that you choose.')
            self.lstFields.setSelectionMode(
                QAbstractItemView.ExtendedSelection)
        self.lblSelectField.setText(question_text)
        self.lstFields.clear()

        default_item = None
        for field in self.parent.layer.dataProvider().fields():
            field_name = field.name()
            item = QListWidgetItem(field_name, self.lstFields)
            item.setData(QtCore.Qt.UserRole, field_name)
            # Select the item if it match the unit's default_attribute
            if unit and 'default_attribute' in unit \
                    and field_name == unit['default_attribute']:
                default_item = item
            # For continuous data, gray out id, gid, fid and text fields
            if self.parent.step_kw_layermode.\
                    selected_layermode() == layer_mode_continuous and unit:
                field_type = field.type()
                if field_type > 9 or re.match(
                        '.{0,2}id$', field_name, re.I):
                    continue  # Don't show unmatched field type

        if default_item:
            self.lstFields.setCurrentItem(default_item)
        self.lblDescribeField.clear()

        # Set values based on existing keywords (if already assigned)
        field_keyword = self.parent.field_keyword_for_the_layer()
        inasafe_field_keywords = self.parent.get_existing_keyword(
            'inasafe_fields')
        if inasafe_field_keywords:
            fields = inasafe_field_keywords.get(field_keyword)
            if isinstance(fields, basestring):
                fields = [fields]
            if fields:
                option_fields = []
                for index in xrange(self.lstFields.count()):
                    option_fields.append(
                        str(self.lstFields.item(index).text()))
                for field in fields:
                    if field in option_fields:
                        self.lstFields.item(option_fields.index(
                            field)).setSelected(True)

        self.auto_select_one_item(self.lstFields)

        if self.selected_fields():
            self.parent.pbnNext.setEnabled(True)
        else:
            self.parent.pbnNext.setEnabled(False)

    @property
    def step_name(self):
        """Get the human friendly name for the wizard step.

        :returns: The name of the wizard step.
        :rtype: str
        """
        return tr('Field Step')

    def help_content(self):
        """Return the content of help for this step wizard.

            We only needs to re-implement this method in each wizard step.

        :returns: A message object contains help.
        :rtype: m.Message
        """
        message = m.Message()
        message.add(m.Paragraph(tr(
            'In this wizard step: {step_name}, you will be able to set the '
            'field that will be used to apply the classification.'
        ).format(step_name=self.step_name)))
        return message
