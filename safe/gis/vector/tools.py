# coding=utf-8

"""Tools for vector layers."""

import logging
from uuid import uuid4
from math import isnan
from PyQt4.QtCore import QPyNullVariant
from qgis.core import (
    QgsGeometry,
    QgsVectorLayer,
    QgsSpatialIndex,
    QgsFeatureRequest,
    QgsCoordinateReferenceSystem,
    QGis,
    QgsFeature,
    QgsField,
    QgsDistanceArea,
    QgsUnitTypes,
    QgsWKBTypes
)

from safe.common.exceptions import MemoryLayerCreationError
from safe.definitions.utilities import definition
from safe.definitions.units import unit_metres, unit_square_metres
from safe.gis.vector.clean_geometry import geometry_checker
from safe.utilities.profiling import profile
from safe.utilities.rounding import convert_unit

__copyright__ = "Copyright 2016, The InaSAFE Project"
__license__ = "GPL version 3"
__email__ = "info@inasafe.org"
__revision__ = '$Format:%H$'

LOGGER = logging.getLogger('InaSAFE')

wkb_type_groups = {
    'Point': (
        QgsWKBTypes.Point,
        QgsWKBTypes.MultiPoint,
        QgsWKBTypes.Point25D,
        QgsWKBTypes.MultiPoint25D,),
    'LineString': (
        QgsWKBTypes.LineString,
        QgsWKBTypes.MultiLineString,
        QgsWKBTypes.LineString25D,
        QgsWKBTypes.MultiLineString25D,),
    'Polygon': (
        QgsWKBTypes.Polygon,
        QgsWKBTypes.MultiPolygon,
        QgsWKBTypes.Polygon25D,
        QgsWKBTypes.MultiPolygon25D,),
}
for key, value in list(wkb_type_groups.items()):
    for const in value:
        wkb_type_groups[const] = key

# This table come from https://qgis.org/api/qgsunittypes_8h_source.html#l00043
distance_unit = {
    0: 'Meters',
    1: 'Kilometres',
    2: 'Feets',
    3: 'Nautical Miles',
    4: 'Yards',
    5: 'Miles',
    6: 'Degrees',
    7: 'Unknown Unit'
}

# This table come from https://qgis.org/api/qgsunittypes_8h_source.html#l00065
area_unit = {
    0: 'Square Meters',
    1: 'Square Kilometres',
    2: 'Square Feet',
    3: 'Square Yards',
    4: 'Square Miles',
    5: 'Hectares',
    6: 'Acres',
    7: 'Square Nautical Miles',
    8: 'Square Degrees',
    9: 'unknown Unit'
}


@profile
def create_memory_layer(
        layer_name, geometry, coordinate_reference_system=None, fields=None):
    """Create a vector memory layer.

    :param layer_name: The name of the layer.
    :type layer_name: str

    :param geometry: The geometry of the layer.
    :rtype geometry: QGis.WkbType

    :param coordinate_reference_system: The CRS of the memory layer.
    :type coordinate_reference_system: QgsCoordinateReferenceSystem

    :param fields: Fields of the vector layer. Default to None.
    :type fields: QgsFields

    :return: The memory layer.
    :rtype: QgsVectorLayer
    """

    if geometry == QGis.Point:
        type_string = 'MultiPoint'
    elif geometry == QGis.Line:
        type_string = 'MultiLineString'
    elif geometry == QGis.Polygon:
        type_string = 'MultiPolygon'
    elif geometry == QGis.NoGeometry:
        type_string = 'none'
    else:
        raise MemoryLayerCreationError(
            'Layer is whether Point nor Line nor Polygon, I got %s' % geometry)

    uri = '%s?index=yes&uuid=%s' % (type_string, str(uuid4()))
    if coordinate_reference_system:
        crs = coordinate_reference_system.authid().lower()
        uri += '&crs=%s' % crs
    memory_layer = QgsVectorLayer(uri, layer_name, 'memory')
    memory_layer.keywords = {
        'inasafe_fields': {}
    }

    if fields:
        data_provider = memory_layer.dataProvider()
        data_provider.addAttributes(fields)
        memory_layer.updateFields()

    return memory_layer


@profile
def copy_layer(source, target):
    """Copy a vector layer to another one.

    :param source: The vector layer to copy.
    :type source: QgsVectorLayer

    :param target: The destination.
    :type source: QgsVectorLayer
    """
    out_feature = QgsFeature()
    target.startEditing()

    request = QgsFeatureRequest()

    aggregation_layer = False
    if source.keywords.get('layer_purpose') == 'aggregation':
        try:
            use_selected_only = source.use_selected_features_only
        except AttributeError:
            use_selected_only = False

        # We need to check if the user wants selected feature only and if there
        # is one minimum selected.
        if use_selected_only and source.selectedFeatureCount() > 0:
            request.setFilterFids(source.selectedFeaturesIds())

        aggregation_layer = True

    for i, feature in enumerate(source.getFeatures(request)):
        geom = feature.geometry()
        if aggregation_layer:
            # See issue https://github.com/inasafe/inasafe/issues/3713
            # and issue https://github.com/inasafe/inasafe/issues/3927
            # Also handle if feature has no geometry.
            geom = geometry_checker(geom)
            if not geom or not geom.isGeosValid():
                LOGGER.info(
                    'One geometry in the aggregation layer is still invalid '
                    'after cleaning.')
        out_feature.setGeometry(QgsGeometry(geom))
        out_feature.setAttributes(feature.attributes())
        target.addFeature(out_feature)

    target.commitChanges()


@profile
def copy_fields(layer, fields_to_copy):
    """Copy fields inside an attribute table.

    :param layer: The vector layer.
    :type layer: QgsVectorLayer

    :param fields_to_copy: Dictionary of fields to copy.
    :type fields_to_copy: dict
    """
    for field in fields_to_copy:

        index = layer.fieldNameIndex(field)
        if index != -1:

            layer.startEditing()

            source_field = layer.fields().at(index)
            new_field = QgsField(source_field)
            new_field.setName(fields_to_copy[field])

            layer.addAttribute(new_field)

            new_index = layer.fieldNameIndex(fields_to_copy[field])

            for feature in layer.getFeatures():
                attributes = feature.attributes()
                source_value = attributes[index]
                layer.changeAttributeValue(
                    feature.id(), new_index, source_value)

            layer.commitChanges()
            layer.updateFields()


@profile
def remove_fields(layer, fields_to_remove):
    """Remove fields from a vector layer.

    :param layer: The vector layer.
    :type layer: QgsVectorLayer

    :param fields_to_remove: List of fields to remove.
    :type fields_to_remove: list
    """
    index_to_remove = []
    data_provider = layer.dataProvider()

    for field in fields_to_remove:
        index = layer.fieldNameIndex(field)
        if index != -1:
            index_to_remove.append(index)

    data_provider.deleteAttributes(index_to_remove)
    layer.updateFields()


@profile
def create_spatial_index(layer):
    """Helper function to create the spatial index on a vector layer.

    This function is mainly used to see the processing time with the decorator.

    :param layer: The vector layer.
    :type layer: QgsVectorLayer

    :return: The index.
    :rtype: QgsSpatialIndex
    """
    spatial_index = QgsSpatialIndex(layer.getFeatures())
    return spatial_index


def create_field_from_definition(field_definition, name=None):
    """Helper to create a field from definition.

    :param field_definition: The definition of the field.
    :type field_definition: safe.definitions.fields

    :param name: The name is required if the field name is dynamic and need a
        string formatting.
    :type name: basestring

    :return: The new field.
    :rtype: QgsField
    """
    field = QgsField()

    if isinstance(name, QPyNullVariant):
        name = 'NULL'

    if name:
        field.setName(field_definition['field_name'] % name)
    else:
        field.setName(field_definition['field_name'])

    if isinstance(field_definition['type'], list):
        # Use the first element in the list of type
        field.setType(field_definition['type'][0])
    else:
        field.setType(field_definition['type'])
    field.setLength(field_definition['length'])
    field.setPrecision(field_definition['precision'])
    return field


def read_dynamic_inasafe_field(inasafe_fields, dynamic_field):
    """Helper to read inasafe_fields using a dynamic field.

    :param inasafe_fields: inasafe_fields keywords to use.
    :type inasafe_fields: dict

    :param dynamic_field: The dynamic field to use.
    :type dynamic_field: safe.definitions.fields

    :return: A list of unique value used in this dynamic field.
    :return: list
    """
    pattern = dynamic_field['key']
    pattern = pattern.replace('%s', '')
    unique_exposure = []
    for key, name_field in inasafe_fields.iteritems():
        if key.endswith(pattern):
            unique_exposure.append(key.replace(pattern, ''))

    return unique_exposure


class SizeCalculator(object):

    """Special object to handle size calculation with an output unit."""

    def __init__(
            self, coordinate_reference_system, geometry_type, exposure_key):
        """Constructor for the size calculator.

        :param coordinate_reference_system: The Coordinate Reference System of
            the layer.
        :type coordinate_reference_system: QgsCoordinateReferenceSystem

        :param exposure_key: The geometry type of the layer.
        :type exposure_key: qgis.core.QgsWkbTypes.GeometryType
        """
        self.calculator = QgsDistanceArea()
        self.calculator.setSourceCrs(coordinate_reference_system)
        self.calculator.setEllipsoid('WGS84')
        self.calculator.setEllipsoidalMode(True)

        if geometry_type == QgsWKBTypes.LineGeometry:
            self.default_unit = unit_metres
            LOGGER.info('The size calculator is set to use {unit}'.format(
                unit=distance_unit[self.calculator.lengthUnits()]))
        else:
            self.default_unit = unit_square_metres
            LOGGER.info('The size calculator is set to use {unit}'.format(
                unit=distance_unit[self.calculator.areaUnits()]))
        self.geometry_type = geometry_type
        self.output_unit = None
        if exposure_key:
            exposure_definition = definition(exposure_key)
            self.output_unit = exposure_definition['size_unit']

    def measure(self, geometry):
        """Measure the lenght or the area of a geometry.

        :param geometry: The geometry.
        :type geometry: QgsGeometry

        :return: The geometric size in the expected exposure unit.
        :rtype: float
        """
        message = 'Size with NaN value : geometry valid={valid}, WKT={wkt}'
        feature_size = 0
        if geometry.isMultipart():
            # Be careful, the size calculator is not working well on a
            # multipart.
            # So we compute the size part per part. See ticket #3812
            for single in geometry.asGeometryCollection():
                if self.geometry_type == QgsWKBTypes.LineGeometry:
                    geometry_size = self.calculator.measureLength(single)
                else:
                    geometry_size = self.calculator.measureArea(single)
                if not isnan(geometry_size):
                    feature_size += geometry_size
                else:
                    LOGGER.debug(message.format(
                        valid=single.isGeosValid(),
                        wkt=single.exportToWkt()))
        else:
            if self.geometry_type == QgsWKBTypes.LineGeometry:
                geometry_size = self.calculator.measureLength(geometry)
            else:
                geometry_size = self.calculator.measureArea(geometry)
            if not isnan(geometry_size):
                feature_size = geometry_size
            else:
                LOGGER.debug(message.format(
                    valid=geometry.isGeosValid(),
                    wkt=geometry.exportToWkt()))

        feature_size = round(feature_size)

        if self.output_unit:
            if self.output_unit != self.default_unit:
                feature_size = convert_unit(
                    feature_size, self.default_unit, self.output_unit)

        return feature_size
