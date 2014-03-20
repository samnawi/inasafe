# coding=utf-8
"""
InaSAFE Disaster risk assessment tool developed by AusAid -
**Test Impact Function Manager**

Contact : ole.moller.nielsen@gmail.com

.. note:: This program is free software; you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation; either version 2 of the License, or
     (at your option) any later version.
"""

__author__ = 'imajimatika@gmail.com'
__revision__ = '$Format:%H$'
__date__ = '20/03/14'
__copyright__ = ('Copyright 2012, Australia Indonesia Facility for '
                 'Disaster Reduction')

import unittest
from safe.impact_functions.impact_function_manager import ImpactFunctionManager
from safe.metadata import small_number


class TestImpactFunctionManager(unittest.TestCase):
    def test_init(self):
        """Test initialize ImpactFunctionManager
        """
        ifm = ImpactFunctionManager()
        expected_result = 12
        result = len(ifm.impact_functions)
        msg = 'I expect ' + str(expected_result) + ' but I got ' +  \
              str(result) + ', please check the number of current enabled ' \
                            'impact functions'
        assert result == expected_result, msg

    def test_allowed_subcategories(self):
        """Test allowed_subcategories API
        """
        ifm = ImpactFunctionManager()
        result = ifm.allowed_subcategories()
        expected_result = ['structure',
                           'earthquake',
                           'population',
                           'all',
                           'flood',
                           'tsunami',
                           'road',
                           'volcano']
        msg = 'I expect ' + str(expected_result) + ' but I got ' + \
              str(result)
        assert set(result) == set(expected_result), msg

    def test_allowed_data_types(self):
        """Test allowed_data_types API
        """
        ifm = ImpactFunctionManager()
        result = ifm.allowed_data_types('flood')
        expected_result = ['polygon', 'numeric']
        msg = 'I expect ' + str(expected_result) + ' but I got ' + \
              str(result)
        assert set(result) == set(expected_result), msg

        result = ifm.allowed_data_types('volcano')
        expected_result = ['point', 'polygon']
        msg = 'I expect ' + str(expected_result) + ' but I got ' + \
              str(result)
        assert set(result) == set(expected_result), msg

        result = ifm.allowed_data_types('structure')
        expected_result = ['polygon']
        msg = 'I expect ' + str(expected_result) + ' but I got ' + \
              str(result)
        assert set(result) == set(expected_result), msg

        result = ifm.allowed_data_types('earthquake')
        expected_result = ['polygon', 'numeric']
        msg = 'I expect ' + str(expected_result) + ' but I got ' + \
              str(result)
        assert set(result) == set(expected_result), msg

        result = ifm.allowed_data_types('tsunami')
        expected_result = ['polygon', 'numeric']
        msg = 'I expect ' + str(expected_result) + ' but I got ' + \
              str(result)
        assert set(result) == set(expected_result), msg

        result = ifm.allowed_data_types('population')
        expected_result = ['numeric']
        msg = 'I expect ' + str(expected_result) + ' but I got ' + \
              str(result)
        assert set(result) == set(expected_result), msg

    def test_allowed_units(self):
        """Test allowed_units API
        """
        ifm = ImpactFunctionManager()
        result = ifm.allowed_units('structure', 'polygon')
        expected_result = [
            {
                'id': 'building_type',
                'constraint': 'unique values',
                'default_attribute': 'type'
            }
        ]
        msg = 'I expect ' + str(expected_result) + ' but I got ' + \
              str(result)
        assert result == expected_result, msg

        result = ifm.allowed_units('structure', 'raster')
        expected_result = []
        msg = 'I expect ' + str(expected_result) + ' but I got ' + \
              str(result)
        assert result == expected_result, msg

        result = ifm.allowed_units('flood', 'numeric')
        expected_result = [
            {
                'id': 'wetdry',
                'constraint': 'categorical',
                'default_attribute': 'affected',
                'default_category': 'wet',
                'classes': [
                    {
                        'name': 'wet',
                        'description': 'Water above ground height.',
                        'string_defaults': ['wet', '1', 'YES', 'y', 'yes'],
                        'numeric_default_min': 1,
                        'numeric_default_max': 9999999999,
                        'optional': True,
                        },
                    {
                        'name': 'dry',
                        'description': 'No water above ground height.',
                        'string_defaults': ['dry', '0', 'No', 'n', 'no'],
                        'numeric_default_min': 0,
                        'numeric_default_max': 1 - small_number,
                        'optional': True
                    }
                ]
            },
            {
                'id': 'metres',
                'constraint': 'continuous',
                'default_attribute': 'depth'  # applies to vector only
            },
            {
                'id': 'feet',
                'constraint': 'continuous',
                'default_attribute': 'depth'  # applies to vector only
            }
        ]
        msg = 'I expect ' + str(expected_result) + ' but I got ' + \
              str(result)
        assert result == expected_result, msg

        result = ifm.allowed_units('earthquake', 'numeric')
        expected_result = [
            {
                'default_attribute': 'depth',
                'id': 'mmi',
                'constraint': 'continuous'
            },
            {
                'id': 'mmi',
                'constraint': 'continuous'
            }
        ]
        msg = 'I expect ' + str(expected_result) + ' but I got ' + \
              str(result)
        assert result == expected_result, msg

if __name__ == '__main__':
    unittest.main()
