"""
Currency Conversion Utilities
Handles multi-currency support with exchange rate integration
"""

from typing import TYPE_CHECKING, Optional, Dict, Any, List
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
import json
import xml.etree.ElementTree as ET

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

# API URLs for exchange rates
ECB_DAILY_RATES_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
ECB_HISTORICAL_RATES_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
FRANKFURTER_API_URL = "https://api.frankfurter.app"  # Alternative free API

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


def get_exchange_rate(
    from_currency: str,
    to_currency: str,
    transaction_date: str = None,
    use_cache: bool = True
) -> float:
    """
    Get exchange rate between two currencies
    
    Args:
        from_currency: Source currency code (e.g., "USD")
        to_currency: Target currency code (e.g., "EUR")
        transaction_date: Date for historical rates (optional)
        use_cache: Whether to use cached rates
        
    Returns:
        Exchange rate as float
    """
    if from_currency == to_currency:
        return 1.0
    
    date_str = transaction_date or nowdate()
    
    # Try to get from ERPNext Currency Exchange
    try:
        rate = frappe.db.get_value(
            "Currency Exchange",
            {
                "from_currency": from_currency,
                "to_currency": to_currency,
                "date": ["<=", date_str]
            },
            "exchange_rate",
            order_by="date desc"
        )
        
        if rate:
            return flt(rate)
    except Exception:
        pass
    
    # Try reverse rate
    try:
        reverse_rate = frappe.db.get_value(
            "Currency Exchange",
            {
                "from_currency": to_currency,
                "to_currency": from_currency,
                "date": ["<=", date_str]
            },
            "exchange_rate",
            order_by="date desc"
        )
        
        if reverse_rate and reverse_rate > 0:
            return 1.0 / flt(reverse_rate)
    except Exception:
        pass
    
    # Fall back to mock rates
    from_rate = MOCK_EXCHANGE_RATES.get(from_currency, 1.0)
    to_rate = MOCK_EXCHANGE_RATES.get(to_currency, 1.0)
    
    if to_rate > 0:
        return from_rate / to_rate
    
    return 1.0


def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
    transaction_date: str = None,
    precision: int = 2
) -> float:
    """
    Convert amount from one currency to another
    
    Args:
        amount: Amount to convert
        from_currency: Source currency code
        to_currency: Target currency code
        transaction_date: Date for historical rates
        precision: Decimal precision for result
        
    Returns:
        Converted amount
    """
    if from_currency == to_currency:
        return round(amount, precision)
    
    rate = get_exchange_rate(from_currency, to_currency, transaction_date)
    converted = flt(amount) * rate
    
    return round(converted, precision)


@frappe.whitelist()
def get_exchange_rate_api(
    from_currency: str,
    to_currency: str,
    transaction_date: str = None
) -> Dict[str, Any]:
    """
    API endpoint for getting exchange rate
    
    Args:
        from_currency: Source currency
        to_currency: Target currency
        transaction_date: Date for rate
        
    Returns:
        Dictionary with rate and metadata
    """
    rate = get_exchange_rate(from_currency, to_currency, transaction_date)
    
    return {
        "from_currency": from_currency,
        "to_currency": to_currency,
        "rate": rate,
        "date": transaction_date or nowdate(),
        "source": "system"
    }


@frappe.whitelist()
def convert_amount_api(
    amount: float,
    from_currency: str,
    to_currency: str,
    transaction_date: str = None
) -> Dict[str, Any]:
    """
    API endpoint for currency conversion
    
    Args:
        amount: Amount to convert
        from_currency: Source currency
        to_currency: Target currency
        transaction_date: Date for rate
        
    Returns:
        Conversion details
    """
    amount = flt(amount)
    rate = get_exchange_rate(from_currency, to_currency, transaction_date)
    converted = convert_currency(amount, from_currency, to_currency, transaction_date)
    
    return {
        "original_amount": amount,
        "from_currency": from_currency,
        "converted_amount": converted,
        "to_currency": to_currency,
        "exchange_rate": rate,
        "date": transaction_date or nowdate()
    }


def update_exchange_rates_from_api() -> Dict[str, Any]:
    """
    Update exchange rates from external API
    
    Uses the European Central Bank (ECB) API to fetch current rates.
    Falls back to Frankfurter API if ECB fails.
    
    Returns:
        Update status and count
    """
    import requests
    
    updated = 0
    errors = []
    rates = {}
    source = "mock_rates"
    
    # Try ECB first (official source, EUR base)
    try:
        rates = fetch_ecb_rates()
        if rates:
            source = "ecb"
    except Exception as e:
        frappe.log_error(f"ECB API error: {str(e)}", "Exchange Rate Update")
    
    # Fallback to Frankfurter API
    if not rates:
        try:
            rates = fetch_frankfurter_rates()
            if rates:
                source = "frankfurter"
        except Exception as e:
            frappe.log_error(f"Frankfurter API error: {str(e)}", "Exchange Rate Update")
    
    # Final fallback to mock rates
    if not rates:
        rates = MOCK_EXCHANGE_RATES.copy()
        source = "mock_rates"
    
    base_currency = "EUR"
    
    for currency, rate in rates.items():
        if currency == base_currency:
            continue
        
        try:
            # Check if exchange rate exists for today
            existing = frappe.db.exists(
                "Currency Exchange",
                {
                    "from_currency": base_currency,
                    "to_currency": currency,
                    "date": nowdate()
                }
            )
            
            if not existing:
                # Create new exchange rate entry
                doc = frappe.get_doc({
                    "doctype": "Currency Exchange",
                    "from_currency": base_currency,
                    "to_currency": currency,
                    "exchange_rate": rate,
                    "date": nowdate(),
                    "for_buying": 1,
                    "for_selling": 1
                })
                doc.insert(ignore_permissions=True)
                updated += 1
            else:
                # Update existing rate if needed
                current_rate = frappe.db.get_value(
                    "Currency Exchange",
                    existing,
                    "exchange_rate"
                )
                if abs(flt(current_rate) - flt(rate)) > 0.0001:
                    frappe.db.set_value(
                        "Currency Exchange",
                        existing,
                        "exchange_rate",
                        rate
                    )
                    updated += 1
                    
        except Exception as e:
            errors.append(f"{currency}: {str(e)}")
    
    if updated > 0:
        frappe.db.commit()
    
    return {
        "updated": updated,
        "errors": errors,
        "source": source,
        "timestamp": frappe.utils.now_datetime()
    }


def fetch_ecb_rates() -> Dict[str, float]:
    """
    Fetch exchange rates from European Central Bank
    
    Returns:
        Dictionary of currency codes to rates (EUR base)
    """
    import requests
    
    response = requests.get(ECB_DAILY_RATES_URL, timeout=10)
    response.raise_for_status()
    
    # Parse XML
    root = ET.fromstring(response.content)
    
    # ECB XML namespace
    namespaces = {
        'gesmes': 'http://www.gesmes.org/xml/2002-08-01',
        'eurofxref': 'http://www.ecb.int/vocabulary/2002-08-01/eurofxref'
    }
    
    rates = {"EUR": 1.0}
    
    # Find all currency elements
    for cube in root.findall('.//eurofxref:Cube[@currency]', namespaces):
        currency = cube.get('currency')
        rate = cube.get('rate')
        if currency and rate:
            rates[currency] = float(rate)
    
    return rates


def fetch_frankfurter_rates(base: str = "EUR") -> Dict[str, float]:
    """
    Fetch exchange rates from Frankfurter API (backed by ECB data)
    
    Args:
        base: Base currency code
        
    Returns:
        Dictionary of currency codes to rates
    """
    import requests
    
    url = f"{FRANKFURTER_API_URL}/latest?from={base}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    
    data = response.json()
    rates = data.get("rates", {})
    rates[base] = 1.0
    
    return rates


def fetch_historical_rate(
    from_currency: str,
    to_currency: str,
    date_str: str
) -> Optional[float]:
    """
    Fetch historical exchange rate from Frankfurter API
    
    Args:
        from_currency: Source currency code
        to_currency: Target currency code
        date_str: Date in YYYY-MM-DD format
        
    Returns:
        Exchange rate or None if not found
    """
    import requests
    
    try:
        url = f"{FRANKFURTER_API_URL}/{date_str}?from={from_currency}&to={to_currency}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return data.get("rates", {}).get(to_currency)
    except Exception:
        return None


def format_currency_amount(
    amount: float,
    currency: str,
    locale: str = "en_US"
) -> str:
    """
    Format amount with currency symbol
    
    Args:
        amount: Amount to format
        currency: Currency code
        locale: Locale for formatting
        
    Returns:
        Formatted string
    """
    # Currency symbols
    symbols = {
        "EUR": "€",
        "USD": "$",
        "GBP": "£",
        "CHF": "CHF",
        "JPY": "¥",
        "CNY": "¥",
        "INR": "₹",
        "PLN": "zł",
        "SEK": "kr",
        "DKK": "kr",
        "NOK": "kr",
        "CZK": "Kč",
        "HUF": "Ft",
        "RON": "lei",
        "BGN": "лв",
        "AUD": "A$",
        "CAD": "C$",
        "BRL": "R$",
        "MXN": "$",
        "KRW": "₩",
        "SGD": "S$",
        "HKD": "HK$",
        "ZAR": "R",
        "RUB": "₽"
    }
    
    symbol = symbols.get(currency, currency)
    
    # Format based on currency conventions
    if currency in ["JPY", "KRW", "HUF"]:
        # No decimals
        formatted = f"{int(amount):,}"
    else:
        formatted = f"{amount:,.2f}"
    
    # Position symbol (before for most, after for some European)
    if currency in ["PLN", "SEK", "DKK", "NOK", "CZK", "HUF", "RON", "BGN"]:
        return f"{formatted} {symbol}"
    else:
        return f"{symbol}{formatted}"


def get_company_currency(company: str) -> str:
    """Get default currency for a company"""
    return frappe.db.get_value("Company", company, "default_currency") or "EUR"


def get_all_exchange_rates(base_currency: str = "EUR") -> Dict[str, float]:
    """
    Get all exchange rates with the given base currency
    
    Args:
        base_currency: The base currency code (default: EUR)
        
    Returns:
        Dictionary of currency codes to exchange rates
    """
    # Return mock rates for offline/testing
    if base_currency == "EUR":
        return MOCK_EXCHANGE_RATES.copy()
    
    # Convert all rates to the requested base
    base_rate = MOCK_EXCHANGE_RATES.get(base_currency, 1.0)
    return {
        currency: rate / base_rate 
        for currency, rate in MOCK_EXCHANGE_RATES.items()
    }


def get_supported_currencies() -> List[Dict[str, str]]:
    """Get list of supported currencies with details"""
    currencies = frappe.get_all(
        "Currency",
        fields=["name", "currency_name", "symbol", "fraction", "fraction_units"],
        filters={"enabled": 1},
        order_by="name"
    )
    
    return currencies
