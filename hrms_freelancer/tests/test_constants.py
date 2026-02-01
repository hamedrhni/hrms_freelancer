# Copyright (c) 2024, HRMS Freelancer and contributors
# For license information, please see license.txt

"""
Unit tests for EU Constants
These tests can run without Frappe installed.
"""

import unittest
import sys
import os

# Add the utils directory to the path so we can import the constants module directly
# This bypasses the __init__.py which has Frappe dependencies
utils_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'utils')
sys.path.insert(0, utils_path)

import constants

EU_COUNTRIES = constants.EU_COUNTRIES
EU_COUNTRY_CODES = constants.EU_COUNTRY_CODES
EU_COUNTRY_NAMES = constants.EU_COUNTRY_NAMES
EUROZONE_COUNTRIES = constants.EUROZONE_COUNTRIES
NON_EUROZONE_EU_COUNTRIES = constants.NON_EUROZONE_EU_COUNTRIES
WITHHOLDING_TAX_RATES = constants.WITHHOLDING_TAX_RATES
GDPR_DATA_RETENTION_PERIODS = constants.GDPR_DATA_RETENTION_PERIODS
CURRENCY_SYMBOLS = constants.CURRENCY_SYMBOLS
get_vat_rate = constants.get_vat_rate
get_country_name = constants.get_country_name
is_eu_country = constants.is_eu_country
is_eurozone_country = constants.is_eurozone_country
get_country_currency = constants.get_country_currency


class TestEUConstants(unittest.TestCase):
    """Test cases for EU constants module"""
    
    def test_all_eu_countries_present(self):
        """Test all 27 EU member states are present"""
        # EU has 27 member states as of 2024
        self.assertEqual(len(EU_COUNTRIES), 27)
    
    def test_eu_country_codes_list(self):
        """Test EU_COUNTRY_CODES matches EU_COUNTRIES keys"""
        self.assertEqual(set(EU_COUNTRY_CODES), set(EU_COUNTRIES.keys()))
    
    def test_eurozone_countries_use_eur(self):
        """Test all eurozone countries have EUR as currency"""
        for code in EUROZONE_COUNTRIES:
            self.assertEqual(
                EU_COUNTRIES[code]['currency'], 
                'EUR',
                f"{code} should use EUR"
            )
    
    def test_non_eurozone_countries_dont_use_eur(self):
        """Test non-eurozone EU countries don't use EUR"""
        for code in NON_EUROZONE_EU_COUNTRIES:
            self.assertNotEqual(
                EU_COUNTRIES[code]['currency'],
                'EUR',
                f"{code} should not use EUR"
            )
    
    def test_vat_rates_are_valid(self):
        """Test all VAT rates are within valid range"""
        for code, info in EU_COUNTRIES.items():
            vat_rate = info['vat_rate']
            self.assertGreaterEqual(vat_rate, 15.0, f"{code} VAT too low")
            self.assertLessEqual(vat_rate, 30.0, f"{code} VAT too high")
    
    def test_get_vat_rate_function(self):
        """Test get_vat_rate helper function"""
        # Test known values
        self.assertEqual(get_vat_rate('DE'), 19.0)  # Germany
        self.assertEqual(get_vat_rate('FR'), 20.0)  # France
        self.assertEqual(get_vat_rate('LU'), 17.0)  # Luxembourg (lowest)
        self.assertEqual(get_vat_rate('HU'), 27.0)  # Hungary (highest)
        
        # Test case insensitivity
        self.assertEqual(get_vat_rate('de'), 19.0)
        
        # Test unknown country
        self.assertEqual(get_vat_rate('XX'), 0.0)
    
    def test_get_country_name_function(self):
        """Test get_country_name helper function"""
        self.assertEqual(get_country_name('DE'), 'Germany')
        self.assertEqual(get_country_name('NL'), 'Netherlands')
        self.assertEqual(get_country_name('de'), 'Germany')  # Case insensitive
        self.assertEqual(get_country_name('XX'), '')  # Unknown
    
    def test_is_eu_country_function(self):
        """Test is_eu_country helper function"""
        # EU countries
        self.assertTrue(is_eu_country('DE'))
        self.assertTrue(is_eu_country('FR'))
        self.assertTrue(is_eu_country('NL'))
        self.assertTrue(is_eu_country('de'))  # Case insensitive
        
        # Non-EU countries
        self.assertFalse(is_eu_country('US'))
        self.assertFalse(is_eu_country('GB'))  # UK left
        self.assertFalse(is_eu_country('CH'))  # Switzerland
        self.assertFalse(is_eu_country('XX'))  # Invalid
    
    def test_is_eurozone_country_function(self):
        """Test is_eurozone_country helper function"""
        # Eurozone
        self.assertTrue(is_eurozone_country('DE'))
        self.assertTrue(is_eurozone_country('FR'))
        self.assertTrue(is_eurozone_country('NL'))
        
        # Non-eurozone EU
        self.assertFalse(is_eurozone_country('PL'))  # Poland
        self.assertFalse(is_eurozone_country('SE'))  # Sweden
        self.assertFalse(is_eurozone_country('DK'))  # Denmark
    
    def test_get_country_currency_function(self):
        """Test get_country_currency helper function"""
        self.assertEqual(get_country_currency('DE'), 'EUR')
        self.assertEqual(get_country_currency('PL'), 'PLN')
        self.assertEqual(get_country_currency('SE'), 'SEK')
        self.assertEqual(get_country_currency('HU'), 'HUF')
        
        # Unknown defaults to EUR
        self.assertEqual(get_country_currency('XX'), 'EUR')
    
    def test_gdpr_retention_periods(self):
        """Test GDPR retention periods are defined"""
        self.assertIn('contracts', GDPR_DATA_RETENTION_PERIODS)
        self.assertIn('payments', GDPR_DATA_RETENTION_PERIODS)
        self.assertIn('personal_data', GDPR_DATA_RETENTION_PERIODS)
        
        # Payments should have longest retention (tax purposes)
        self.assertGreaterEqual(
            GDPR_DATA_RETENTION_PERIODS['payments'],
            GDPR_DATA_RETENTION_PERIODS['personal_data']
        )
    
    def test_currency_symbols_defined(self):
        """Test currency symbols are defined for main currencies"""
        self.assertEqual(CURRENCY_SYMBOLS['EUR'], '€')
        self.assertEqual(CURRENCY_SYMBOLS['USD'], '$')
        self.assertEqual(CURRENCY_SYMBOLS['GBP'], '£')
        self.assertEqual(CURRENCY_SYMBOLS['PLN'], 'zł')


class TestWithholdingTaxRates(unittest.TestCase):
    """Test cases for withholding tax rates"""
    
    def test_standard_rates_defined(self):
        """Test standard withholding tax rates are defined"""
        self.assertIn('services', WITHHOLDING_TAX_RATES)
        self.assertIn('royalties', WITHHOLDING_TAX_RATES)
        self.assertIn('interest', WITHHOLDING_TAX_RATES)
        self.assertIn('dividends', WITHHOLDING_TAX_RATES)
    
    def test_rates_are_valid_percentages(self):
        """Test all rates are valid percentages"""
        for category, rate in WITHHOLDING_TAX_RATES.items():
            self.assertGreaterEqual(rate, 0, f"{category} rate negative")
            self.assertLessEqual(rate, 50, f"{category} rate too high")


if __name__ == "__main__":
    unittest.main()
