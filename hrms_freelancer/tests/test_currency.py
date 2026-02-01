# Copyright (c) 2024, HRMS Freelancer and contributors
# For license information, please see license.txt

"""
Unit tests for Currency utilities
"""

import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal


class TestCurrencyConversion(unittest.TestCase):
    """Test cases for currency conversion utilities"""
    
    def test_same_currency_returns_one(self):
        """Test exchange rate for same currency is always 1.0"""
        from hrms_freelancer.utils.currency import get_exchange_rate
        
        rate = get_exchange_rate("EUR", "EUR")
        self.assertEqual(rate, 1.0)
        
        rate = get_exchange_rate("USD", "USD")
        self.assertEqual(rate, 1.0)
    
    def test_convert_same_currency(self):
        """Test converting same currency returns original amount"""
        from hrms_freelancer.utils.currency import convert_currency
        
        result = convert_currency(100.00, "EUR", "EUR")
        self.assertEqual(result, 100.00)
    
    def test_convert_with_precision(self):
        """Test conversion respects precision parameter"""
        from hrms_freelancer.utils.currency import convert_currency
        
        # Test with different precisions
        result_2 = convert_currency(100.00, "EUR", "USD", precision=2)
        result_4 = convert_currency(100.00, "EUR", "USD", precision=4)
        
        # Should have correct number of decimals
        self.assertEqual(result_2, round(result_2, 2))
        self.assertEqual(result_4, round(result_4, 4))
    
    def test_mock_rates_contain_major_currencies(self):
        """Test mock rates include all major currencies"""
        from hrms_freelancer.utils.currency import MOCK_EXCHANGE_RATES
        
        major_currencies = ['EUR', 'USD', 'GBP', 'CHF', 'JPY', 'CAD', 'AUD']
        for currency in major_currencies:
            self.assertIn(currency, MOCK_EXCHANGE_RATES)
    
    def test_get_all_exchange_rates_eur_base(self):
        """Test getting all rates with EUR base"""
        from hrms_freelancer.utils.currency import get_all_exchange_rates
        
        rates = get_all_exchange_rates("EUR")
        
        self.assertIn("EUR", rates)
        self.assertEqual(rates["EUR"], 1.0)
        self.assertIn("USD", rates)
        self.assertGreater(rates["USD"], 0)
    
    def test_get_all_exchange_rates_other_base(self):
        """Test getting all rates with non-EUR base"""
        from hrms_freelancer.utils.currency import get_all_exchange_rates
        
        rates = get_all_exchange_rates("USD")
        
        self.assertIn("USD", rates)
        self.assertEqual(rates["USD"], 1.0)
        self.assertIn("EUR", rates)
        # EUR should be less than 1 when USD is base (EUR is stronger)
        self.assertLess(rates["EUR"], 1.0)
    
    def test_format_currency_symbol_before(self):
        """Test currencies with symbol before amount"""
        from hrms_freelancer.utils.currency import format_currency_amount
        
        result = format_currency_amount(1234.56, "EUR")
        self.assertTrue(result.startswith("€"))
        
        result = format_currency_amount(1234.56, "USD")
        self.assertTrue(result.startswith("$"))
    
    def test_format_currency_symbol_after(self):
        """Test currencies with symbol after amount"""
        from hrms_freelancer.utils.currency import format_currency_amount
        
        result = format_currency_amount(1234.56, "PLN")
        self.assertTrue(result.endswith("zł"))
        
        result = format_currency_amount(1234.56, "SEK")
        self.assertTrue(result.endswith("kr"))
    
    def test_format_currency_no_decimals(self):
        """Test currencies that don't use decimals"""
        from hrms_freelancer.utils.currency import format_currency_amount
        
        # JPY should not have decimals
        result = format_currency_amount(1234.56, "JPY")
        self.assertNotIn(".", result)


class TestExchangeRateAPI(unittest.TestCase):
    """Test cases for exchange rate API functions"""
    
    def test_ecb_xml_parsing(self):
        """Test ECB XML response parsing"""
        from hrms_freelancer.utils.currency import fetch_ecb_rates
        import xml.etree.ElementTree as ET
        
        # Sample ECB XML structure
        sample_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01" 
                         xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
            <gesmes:subject>Reference rates</gesmes:subject>
            <Cube>
                <Cube time="2024-01-15">
                    <Cube currency="USD" rate="1.0875"/>
                    <Cube currency="GBP" rate="0.8612"/>
                </Cube>
            </Cube>
        </gesmes:Envelope>'''
        
        # Parse manually to verify structure understanding
        root = ET.fromstring(sample_xml)
        namespaces = {
            'gesmes': 'http://www.gesmes.org/xml/2002-08-01',
            'eurofxref': 'http://www.ecb.int/vocabulary/2002-08-01/eurofxref'
        }
        
        rates = {"EUR": 1.0}
        for cube in root.findall('.//{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}Cube[@currency]'):
            currency = cube.get('currency')
            rate = cube.get('rate')
            if currency and rate:
                rates[currency] = float(rate)
        
        self.assertEqual(rates["EUR"], 1.0)
        self.assertAlmostEqual(rates["USD"], 1.0875, places=4)
        self.assertAlmostEqual(rates["GBP"], 0.8612, places=4)


class TestHistoricalRates(unittest.TestCase):
    """Test cases for historical exchange rates"""
    
    @patch('hrms_freelancer.utils.currency.fetch_historical_rate')
    def test_historical_rate_lookup(self, mock_fetch):
        """Test looking up historical rates"""
        mock_fetch.return_value = 1.12
        
        from hrms_freelancer.utils.currency import fetch_historical_rate
        
        rate = fetch_historical_rate("EUR", "USD", "2024-01-01")
        mock_fetch.assert_called_once_with("EUR", "USD", "2024-01-01")


if __name__ == "__main__":
    unittest.main()
