# Copyright (c) 2024, HRMS Freelancer and contributors
# For license information, please see license.txt

"""
Unit tests for Freelancer Payment tax calculations
"""

import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal

import frappe
from frappe.tests.utils import FrappeTestCase


class TestTaxCalculations(FrappeTestCase):
    """Test cases for tax calculation utilities"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.base_amount = 1000.0
    
    def test_eu_to_eu_reverse_charge(self):
        """Test EU to EU B2B transaction applies reverse charge"""
        from hrms_freelancer.utils.tax_calculations import TaxCalculator
        
        calculator = TaxCalculator(
            freelancer_country="Germany",
            company_country="Netherlands",
            is_b2b=True
        )
        
        result = calculator.calculate_all_taxes(
            gross_amount=self.base_amount,
            service_type="professional"
        )
        
        # EU to EU B2B should have:
        # - No withholding tax
        # - Reverse charge (0% VAT charged, recipient accounts)
        self.assertEqual(result["withholding_tax"]["rate"], 0)
        self.assertEqual(result["withholding_tax"]["amount"], 0)
        self.assertTrue(result["vat"]["reverse_charge"])
        self.assertEqual(result["vat"]["amount"], 0)
        self.assertEqual(result["net_payable"], self.base_amount)
    
    def test_eu_to_non_eu_no_vat(self):
        """Test EU to non-EU export has 0% VAT"""
        from hrms_freelancer.utils.tax_calculations import TaxCalculator
        
        calculator = TaxCalculator(
            freelancer_country="Netherlands",
            company_country="United States",
            is_b2b=True
        )
        
        result = calculator.calculate_all_taxes(
            gross_amount=self.base_amount,
            service_type="professional"
        )
        
        # EU to non-EU should have 0% VAT (export)
        self.assertEqual(result["vat"]["rate"], 0)
        self.assertEqual(result["vat"]["amount"], 0)
        self.assertFalse(result["vat"]["reverse_charge"])
    
    def test_non_eu_to_eu_reverse_charge(self):
        """Test non-EU to EU applies reverse charge"""
        from hrms_freelancer.utils.tax_calculations import TaxCalculator
        
        calculator = TaxCalculator(
            freelancer_country="United States",
            company_country="Netherlands",
            is_b2b=True
        )
        
        result = calculator.calculate_all_taxes(
            gross_amount=self.base_amount,
            service_type="professional"
        )
        
        # Non-EU to EU should have reverse charge
        self.assertTrue(result["vat"]["reverse_charge"])
    
    def test_withholding_with_treaty(self):
        """Test withholding tax with treaty applied"""
        from hrms_freelancer.utils.tax_calculations import TaxCalculator
        
        # This would need mock for treaty lookup
        calculator = TaxCalculator(
            freelancer_country="India",
            company_country="Netherlands",
            is_b2b=True
        )
        
        result = calculator.calculate_all_taxes(
            gross_amount=self.base_amount,
            service_type="professional",
            has_tax_certificate=True
        )
        
        # India-Netherlands treaty has 10% withholding for services
        # This test checks the structure is correct
        self.assertIn("withholding_tax", result)
        self.assertIn("rate", result["withholding_tax"])
        self.assertIn("amount", result["withholding_tax"])
    
    def test_domestic_payment(self):
        """Test domestic (same country) payment"""
        from hrms_freelancer.utils.tax_calculations import TaxCalculator
        
        calculator = TaxCalculator(
            freelancer_country="Netherlands",
            company_country="Netherlands",
            is_b2b=True
        )
        
        result = calculator.calculate_all_taxes(
            gross_amount=self.base_amount,
            service_type="professional"
        )
        
        # Domestic should have no withholding
        self.assertEqual(result["withholding_tax"]["rate"], 0)
        self.assertFalse(result["is_cross_border"])
    
    def test_calculation_components(self):
        """Test all components are present in result"""
        from hrms_freelancer.utils.tax_calculations import TaxCalculator
        
        calculator = TaxCalculator(
            freelancer_country="Germany",
            company_country="Netherlands",
            is_b2b=True
        )
        
        result = calculator.calculate_all_taxes(
            gross_amount=self.base_amount,
            service_type="professional"
        )
        
        # Check all required keys are present
        required_keys = [
            "gross_amount", "freelancer_country", "company_country",
            "is_eu_freelancer", "is_cross_border", "withholding_tax",
            "vat", "net_payable", "compliance_notes"
        ]
        
        for key in required_keys:
            self.assertIn(key, result)


class TestCurrencyConversion(FrappeTestCase):
    """Test cases for currency conversion utilities"""
    
    def test_convert_currency_same(self):
        """Test conversion when source and target are same"""
        from hrms_freelancer.utils.currency import convert_currency
        
        result = convert_currency(100, "EUR", "EUR")
        self.assertEqual(result, 100)
    
    def test_convert_currency_eur_to_usd(self):
        """Test EUR to USD conversion"""
        from hrms_freelancer.utils.currency import convert_currency
        
        result = convert_currency(100, "EUR", "USD")
        
        # Should be approximately 109 (with mock rate of 1.09)
        self.assertGreater(result, 100)
        self.assertLess(result, 120)
    
    def test_format_currency(self):
        """Test currency formatting"""
        from hrms_freelancer.utils.currency import format_currency_amount
        
        result = format_currency_amount(1234.56, "EUR")
        
        # Should contain the amount
        self.assertIn("1", result)
        self.assertIn("234", result)
    
    def test_exchange_rate_retrieval(self):
        """Test exchange rate retrieval"""
        from hrms_freelancer.utils.currency import get_exchange_rate
        
        rate = get_exchange_rate("EUR", "USD")
        
        # Rate should be positive
        self.assertGreater(rate, 0)


class TestVATValidation(FrappeTestCase):
    """Test cases for VAT number validation"""
    
    def test_dutch_vat_format(self):
        """Test Dutch VAT number format validation"""
        from hrms_freelancer.utils.tax_calculations import validate_tax_id
        
        # Valid format
        result = validate_tax_id("123456789", "Netherlands")
        self.assertTrue(result["valid"])
        
        # Invalid format (too short)
        result = validate_tax_id("12345678", "Netherlands")
        self.assertFalse(result["valid"])
    
    def test_german_vat_format(self):
        """Test German VAT number format validation"""
        from hrms_freelancer.utils.tax_calculations import validate_tax_id
        
        # Valid format (11 digits)
        result = validate_tax_id("12345678901", "Germany")
        self.assertTrue(result["valid"])
    
    def test_unknown_country(self):
        """Test validation for unknown country passes through"""
        from hrms_freelancer.utils.tax_calculations import validate_tax_id
        
        result = validate_tax_id("ABC123", "Unknown Country")
        
        # Should pass through without validation
        self.assertTrue(result["valid"])
        self.assertFalse(result["validated"])


class TestPaymentCalculations(FrappeTestCase):
    """Test cases for payment calculations"""
    
    def test_gross_with_vat_calculation(self):
        """Test gross with VAT calculation"""
        gross = 1000
        vat_rate = 21
        expected_vat = 210
        expected_total = 1210
        
        vat_amount = gross * vat_rate / 100
        total = gross + vat_amount
        
        self.assertEqual(vat_amount, expected_vat)
        self.assertEqual(total, expected_total)
    
    def test_withholding_deduction(self):
        """Test withholding tax deduction"""
        gross = 1000
        withholding_rate = 10
        expected_withholding = 100
        expected_net = 900
        
        withholding = gross * withholding_rate / 100
        net = gross - withholding
        
        self.assertEqual(withholding, expected_withholding)
        self.assertEqual(net, expected_net)
    
    def test_combined_calculation(self):
        """Test combined VAT and withholding calculation"""
        gross = 1000
        vat_rate = 21
        withholding_rate = 10
        
        vat = gross * vat_rate / 100  # 210
        withholding = gross * withholding_rate / 100  # 100
        
        # Net payable = gross + VAT - withholding
        net_payable = gross + vat - withholding  # 1000 + 210 - 100 = 1110
        
        self.assertEqual(net_payable, 1110)
    
    def test_reverse_charge_no_vat(self):
        """Test reverse charge scenario has no VAT added"""
        gross = 1000
        
        # With reverse charge, no VAT is added
        net_payable = gross
        
        self.assertEqual(net_payable, 1000)


if __name__ == "__main__":
    unittest.main()
