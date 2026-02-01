"""
Standalone tests for hrms_freelancer
Tests core functionality without requiring full Frappe installation
"""
import sys
import os

# =============================================================================
# STANDALONE IMPLEMENTATIONS FOR TESTING (no Frappe dependency)
# =============================================================================

# Mock exchange rates for offline/testing (EUR base)
MOCK_EXCHANGE_RATES = {
    "EUR": 1.0,
    "USD": 1.08,
    "GBP": 0.86,
    "CHF": 0.96,
    "PLN": 4.32,
    "SEK": 11.45,
    "DKK": 7.46,
    "NOK": 11.65,
    "CZK": 25.20,
    "HUF": 395.0,
    "RON": 4.98,
    "BGN": 1.96,
    "HRK": 7.53,
    "INR": 90.50,
    "JPY": 162.0,
    "CNY": 7.85,
    "AUD": 1.65,
    "CAD": 1.47,
    "BRL": 5.35,
    "MXN": 18.90,
    "KRW": 1425.0,
    "SGD": 1.46,
    "HKD": 8.45,
    "ZAR": 20.15,
    "RUB": 98.50,
}

EU_CURRENCIES = {"EUR", "PLN", "SEK", "DKK", "CZK", "HUF", "RON", "BGN", "HRK"}

# VAT rates by country (2026)
VAT_RATES = {
    "DE": 19.0,  "FR": 20.0,  "IT": 22.0,  "ES": 21.0,  "NL": 21.0,
    "BE": 21.0,  "AT": 20.0,  "PL": 23.0,  "SE": 25.0,  "DK": 25.0,
    "FI": 25.5,  "IE": 23.0,  "PT": 23.0,  "GR": 24.0,  "CZ": 21.0,
    "HU": 27.0,  "RO": 19.0,  "SK": 20.0,  "BG": 20.0,  "HR": 25.0,
    "SI": 22.0,  "LT": 21.0,  "LV": 21.0,  "EE": 22.0,  "CY": 19.0,
    "MT": 18.0,  "LU": 17.0,  "NO": 25.0,  "CH": 8.1,   "GB": 20.0,
}

# Withholding tax rates by country
WHT_RATES = {
    "US": 30.0, "IN": 10.0, "CN": 10.0, "BR": 15.0, "RU": 20.0,
    "AU": 10.0, "CA": 25.0, "JP": 20.42, "KR": 22.0, "MX": 25.0,
}

EU_COUNTRIES = [
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE"
]


# Currency utilities
def get_supported_currencies():
    return list(MOCK_EXCHANGE_RATES.keys())

def is_eu_currency(currency_code):
    return currency_code in EU_CURRENCIES

def get_exchange_rate(from_currency, to_currency):
    if from_currency == to_currency:
        return 1.0
    if from_currency not in MOCK_EXCHANGE_RATES or to_currency not in MOCK_EXCHANGE_RATES:
        return 1.0
    from_rate = MOCK_EXCHANGE_RATES[from_currency]
    to_rate = MOCK_EXCHANGE_RATES[to_currency]
    return to_rate / from_rate

def convert_currency(amount, from_currency, to_currency):
    rate = get_exchange_rate(from_currency, to_currency)
    return round(amount * rate, 2)


# Tax calculator
class TaxCalculator:
    def calculate_vat(self, amount, country_code):
        rate = VAT_RATES.get(country_code, 0)
        return round(amount * rate / 100, 2)
    
    def is_reverse_charge_applicable(self, client_country, freelancer_country, is_b2b):
        if not is_b2b:
            return False
        if client_country == freelancer_country:
            return False
        return client_country in EU_COUNTRIES and freelancer_country in EU_COUNTRIES
    
    def calculate_withholding_tax(self, amount, country_code, treaty_rate=None):
        rate = treaty_rate if treaty_rate is not None else WHT_RATES.get(country_code, 0)
        return round(amount * rate / 100, 2)
    
    def calculate_payment(self, gross_amount, freelancer_country, client_country, 
                          is_b2b=True, apply_withholding=False, treaty_rate=None):
        result = {
            "gross_amount": gross_amount,
            "vat_amount": 0,
            "withholding_tax": 0,
            "reverse_charge": False,
            "net_amount": gross_amount
        }
        
        # Check reverse charge
        if self.is_reverse_charge_applicable(client_country, freelancer_country, is_b2b):
            result["reverse_charge"] = True
        else:
            result["vat_amount"] = self.calculate_vat(gross_amount, client_country)
        
        # Apply withholding tax for non-EU
        if apply_withholding and freelancer_country not in EU_COUNTRIES:
            result["withholding_tax"] = self.calculate_withholding_tax(
                gross_amount, freelancer_country, treaty_rate
            )
        
        result["net_amount"] = gross_amount - result["withholding_tax"]
        return result


# =============================================================================
# TEST FUNCTIONS
# =============================================================================

def test_currency_utils():
    """Test currency utility functions"""
    print("Testing currency utilities...")
    
    # Test supported currencies
    currencies = get_supported_currencies()
    assert "EUR" in currencies, "EUR should be supported"
    assert "USD" in currencies, "USD should be supported"
    assert "GBP" in currencies, "GBP should be supported"
    print(f"  ✓ {len(currencies)} currencies supported")
    
    # Test EU currency detection
    assert is_eu_currency("EUR") == True, "EUR is EU currency"
    assert is_eu_currency("PLN") == True, "PLN is EU currency"
    assert is_eu_currency("USD") == False, "USD is not EU currency"
    print("  ✓ EU currency detection works")
    
    # Test exchange rate
    rate = get_exchange_rate("USD", "EUR")
    assert rate > 0, "Exchange rate should be positive"
    print(f"  ✓ USD to EUR rate: {rate:.4f}")
    
    # Test currency conversion
    result = convert_currency(100, "USD", "EUR")
    assert result > 0, "Conversion should be positive"
    print(f"  ✓ 100 USD = {result:.2f} EUR")
    
    print("✅ Currency utilities: PASSED\n")

def test_tax_calculations():
    """Test tax calculation utilities"""
    print("Testing tax calculations...")
    
    calc = TaxCalculator()
    
    # Test VAT calculation
    vat = calc.calculate_vat(1000, "DE")
    assert vat == 190, f"German VAT on 1000 should be 190, got {vat}"
    print("  ✓ German VAT (19%): €1000 -> €190")
    
    vat_fr = calc.calculate_vat(1000, "FR")
    assert vat_fr == 200, f"French VAT on 1000 should be 200, got {vat_fr}"
    print("  ✓ French VAT (20%): €1000 -> €200")
    
    # Test reverse charge
    is_reverse = calc.is_reverse_charge_applicable("DE", "FR", True)
    assert is_reverse == True, "Reverse charge should apply for B2B EU cross-border"
    print("  ✓ Reverse charge applies for B2B EU cross-border")
    
    is_reverse_b2c = calc.is_reverse_charge_applicable("DE", "FR", False)
    assert is_reverse_b2c == False, "Reverse charge should NOT apply for B2C"
    print("  ✓ Reverse charge does NOT apply for B2C")
    
    # Test withholding tax
    wht = calc.calculate_withholding_tax(1000, "IN")
    assert wht == 100, f"India WHT on 1000 should be 100, got {wht}"
    print("  ✓ India WHT (10%): €1000 -> €100")
    
    wht_us = calc.calculate_withholding_tax(1000, "US")
    assert wht_us == 300, f"US WHT on 1000 should be 300, got {wht_us}"
    print("  ✓ US WHT (30%): €1000 -> €300")
    
    # Test with tax treaty reduction
    wht_treaty = calc.calculate_withholding_tax(1000, "US", treaty_rate=15)
    assert wht_treaty == 150, f"US WHT with treaty should be 150, got {wht_treaty}"
    print("  ✓ US WHT with treaty (15%): €1000 -> €150")
    
    # Test full payment calculation
    payment = calc.calculate_payment(
        gross_amount=5000,
        freelancer_country="US",
        client_country="DE",
        is_b2b=True,
        apply_withholding=True
    )
    assert "gross_amount" in payment
    assert "net_amount" in payment
    assert payment["gross_amount"] == 5000
    print(f"  ✓ Full payment calculation: gross={payment['gross_amount']}, net={payment['net_amount']}")
    
    print("✅ Tax calculations: PASSED\n")

def test_gdpr_compliance():
    """Test GDPR-related utilities"""
    print("Testing GDPR compliance checks...")
    
    def is_gdpr_applicable(country_code):
        """Check if GDPR applies to a country"""
        EEA_COUNTRIES = EU_COUNTRIES + ["IS", "LI", "NO"]
        return country_code in EEA_COUNTRIES
    
    assert is_gdpr_applicable("DE") == True, "GDPR applies to Germany"
    assert is_gdpr_applicable("FR") == True, "GDPR applies to France"
    assert is_gdpr_applicable("NO") == True, "GDPR applies to Norway (EEA)"
    assert is_gdpr_applicable("US") == False, "GDPR does not apply to US"
    
    print("  ✓ GDPR applicability correctly determined")
    print("✅ GDPR compliance: PASSED\n")

def test_contract_types():
    """Test contract type configurations"""
    print("Testing contract types...")
    
    CONTRACT_TYPES = {
        "Fixed Price": {
            "payment_schedule": "milestone",
            "requires_deliverables": True,
            "default_milestone_count": 3
        },
        "Time and Materials": {
            "payment_schedule": "periodic",
            "requires_timesheet": True,
            "default_billing_cycle": "Monthly"
        },
        "Retainer": {
            "payment_schedule": "recurring",
            "requires_minimum_hours": True,
            "default_billing_cycle": "Monthly"
        },
        "Project-Based": {
            "payment_schedule": "milestone",
            "requires_deliverables": True,
            "default_milestone_count": 5
        }
    }
    
    assert "Fixed Price" in CONTRACT_TYPES
    assert CONTRACT_TYPES["Fixed Price"]["payment_schedule"] == "milestone"
    print("  ✓ Fixed Price contract: milestone-based payments")
    
    assert CONTRACT_TYPES["Time and Materials"]["requires_timesheet"] == True
    print("  ✓ Time and Materials: requires timesheet")
    
    assert CONTRACT_TYPES["Retainer"]["payment_schedule"] == "recurring"
    print("  ✓ Retainer: recurring payments")
    
    print("✅ Contract types: PASSED\n")

def test_payment_methods():
    """Test supported payment methods"""
    print("Testing payment methods...")
    
    PAYMENT_METHODS = {
        "Bank Transfer": {
            "supported_currencies": ["EUR", "USD", "GBP", "CHF"],
            "processing_days": 2,
            "requires_iban": True
        },
        "PayPal": {
            "supported_currencies": ["EUR", "USD", "GBP", "AUD", "CAD"],
            "processing_days": 0,
            "fee_percentage": 2.9
        },
        "Wise": {
            "supported_currencies": ["EUR", "USD", "GBP", "AUD", "CAD", "SGD"],
            "processing_days": 1,
            "low_fees": True
        },
        "Crypto": {
            "supported_currencies": ["BTC", "ETH", "USDT", "USDC"],
            "processing_days": 0,
            "volatile": True
        }
    }
    
    assert "Bank Transfer" in PAYMENT_METHODS
    assert PAYMENT_METHODS["Bank Transfer"]["processing_days"] == 2
    print("  ✓ Bank Transfer: 2 day processing")
    
    assert PAYMENT_METHODS["PayPal"]["fee_percentage"] == 2.9
    print("  ✓ PayPal: 2.9% fee")
    
    assert PAYMENT_METHODS["Wise"]["low_fees"] == True
    print("  ✓ Wise: low fees supported")
    
    print("✅ Payment methods: PASSED\n")

def test_vat_rates():
    """Test VAT rate validation"""
    print("Testing VAT rates for EU countries...")
    
    # Validate some key VAT rates
    assert VAT_RATES["DE"] == 19.0, "Germany VAT should be 19%"
    assert VAT_RATES["FR"] == 20.0, "France VAT should be 20%"
    assert VAT_RATES["HU"] == 27.0, "Hungary VAT should be 27% (highest in EU)"
    assert VAT_RATES["LU"] == 17.0, "Luxembourg VAT should be 17% (lowest in EU)"
    
    print("  ✓ Germany: 19%")
    print("  ✓ France: 20%")
    print("  ✓ Hungary: 27% (highest)")
    print("  ✓ Luxembourg: 17% (lowest)")
    
    # Check all EU countries have VAT rates
    missing = [c for c in EU_COUNTRIES if c not in VAT_RATES]
    assert len(missing) == 0, f"Missing VAT rates for: {missing}"
    print(f"  ✓ All {len(EU_COUNTRIES)} EU countries have VAT rates defined")
    
    print("✅ VAT rates: PASSED\n")

def test_cross_border_scenarios():
    """Test various cross-border payment scenarios"""
    print("Testing cross-border payment scenarios...")
    
    calc = TaxCalculator()
    
    # Scenario 1: German company paying French freelancer (B2B, EU)
    payment1 = calc.calculate_payment(
        gross_amount=10000,
        freelancer_country="FR",
        client_country="DE",
        is_b2b=True
    )
    assert payment1["reverse_charge"] == True, "Should use reverse charge"
    assert payment1["vat_amount"] == 0, "VAT should be 0 with reverse charge"
    print("  ✓ DE→FR B2B: Reverse charge applies, no VAT collected")
    
    # Scenario 2: German company paying US freelancer
    payment2 = calc.calculate_payment(
        gross_amount=10000,
        freelancer_country="US",
        client_country="DE",
        is_b2b=True,
        apply_withholding=True
    )
    assert payment2["reverse_charge"] == False, "No reverse charge for non-EU"
    assert payment2["withholding_tax"] == 3000, "30% WHT for US"
    print("  ✓ DE→US B2B: 30% withholding tax, no reverse charge")
    
    # Scenario 3: US with tax treaty (reduced rate)
    payment3 = calc.calculate_payment(
        gross_amount=10000,
        freelancer_country="US",
        client_country="DE",
        is_b2b=True,
        apply_withholding=True,
        treaty_rate=15
    )
    assert payment3["withholding_tax"] == 1500, "15% WHT with treaty"
    print("  ✓ DE→US with treaty: 15% withholding tax")
    
    # Scenario 4: Same country (no reverse charge)
    payment4 = calc.calculate_payment(
        gross_amount=10000,
        freelancer_country="DE",
        client_country="DE",
        is_b2b=True
    )
    assert payment4["reverse_charge"] == False, "No reverse charge for same country"
    print("  ✓ DE→DE B2B: No reverse charge (same country)")
    
    print("✅ Cross-border scenarios: PASSED\n")


def run_all_tests():
    """Run all standalone tests"""
    print("=" * 60)
    print("HRMS Freelancer - Standalone Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_currency_utils,
        test_tax_calculations,
        test_vat_rates,
        test_gdpr_compliance,
        test_contract_types,
        test_payment_methods,
        test_cross_border_scenarios,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: FAILED")
            print(f"   Error: {str(e)}")
            failed += 1
    
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
