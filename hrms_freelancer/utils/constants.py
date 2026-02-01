"""
EU Constants and Reference Data for HRMS Freelancer

This module centralizes all EU-related constants to ensure consistency
across the application and simplify maintenance.
"""

# EU Member States with VAT information
# Format: {country_code: {'name': full_name, 'vat_rate': standard_rate, 'currency': main_currency}}
EU_COUNTRIES = {
    'AT': {'name': 'Austria', 'vat_rate': 20.0, 'currency': 'EUR'},
    'BE': {'name': 'Belgium', 'vat_rate': 21.0, 'currency': 'EUR'},
    'BG': {'name': 'Bulgaria', 'vat_rate': 20.0, 'currency': 'BGN'},
    'HR': {'name': 'Croatia', 'vat_rate': 25.0, 'currency': 'EUR'},
    'CY': {'name': 'Cyprus', 'vat_rate': 19.0, 'currency': 'EUR'},
    'CZ': {'name': 'Czech Republic', 'vat_rate': 21.0, 'currency': 'CZK'},
    'DK': {'name': 'Denmark', 'vat_rate': 25.0, 'currency': 'DKK'},
    'EE': {'name': 'Estonia', 'vat_rate': 22.0, 'currency': 'EUR'},
    'FI': {'name': 'Finland', 'vat_rate': 24.0, 'currency': 'EUR'},
    'FR': {'name': 'France', 'vat_rate': 20.0, 'currency': 'EUR'},
    'DE': {'name': 'Germany', 'vat_rate': 19.0, 'currency': 'EUR'},
    'GR': {'name': 'Greece', 'vat_rate': 24.0, 'currency': 'EUR'},
    'HU': {'name': 'Hungary', 'vat_rate': 27.0, 'currency': 'HUF'},
    'IE': {'name': 'Ireland', 'vat_rate': 23.0, 'currency': 'EUR'},
    'IT': {'name': 'Italy', 'vat_rate': 22.0, 'currency': 'EUR'},
    'LV': {'name': 'Latvia', 'vat_rate': 21.0, 'currency': 'EUR'},
    'LT': {'name': 'Lithuania', 'vat_rate': 21.0, 'currency': 'EUR'},
    'LU': {'name': 'Luxembourg', 'vat_rate': 17.0, 'currency': 'EUR'},
    'MT': {'name': 'Malta', 'vat_rate': 18.0, 'currency': 'EUR'},
    'NL': {'name': 'Netherlands', 'vat_rate': 21.0, 'currency': 'EUR'},
    'PL': {'name': 'Poland', 'vat_rate': 23.0, 'currency': 'PLN'},
    'PT': {'name': 'Portugal', 'vat_rate': 23.0, 'currency': 'EUR'},
    'RO': {'name': 'Romania', 'vat_rate': 19.0, 'currency': 'RON'},
    'SK': {'name': 'Slovakia', 'vat_rate': 20.0, 'currency': 'EUR'},
    'SI': {'name': 'Slovenia', 'vat_rate': 22.0, 'currency': 'EUR'},
    'ES': {'name': 'Spain', 'vat_rate': 21.0, 'currency': 'EUR'},
    'SE': {'name': 'Sweden', 'vat_rate': 25.0, 'currency': 'SEK'},
}

# List of EU country codes
EU_COUNTRY_CODES = list(EU_COUNTRIES.keys())

# List of EU country names
EU_COUNTRY_NAMES = [info['name'] for info in EU_COUNTRIES.values()]

# Eurozone countries (countries using EUR as main currency)
EUROZONE_COUNTRIES = [code for code, info in EU_COUNTRIES.items() if info['currency'] == 'EUR']

# Non-Eurozone EU countries
NON_EUROZONE_EU_COUNTRIES = [code for code, info in EU_COUNTRIES.items() if info['currency'] != 'EUR']

# Common treaty countries (countries with tax treaties relevant for freelancers)
TREATY_COUNTRIES = [
    'US', 'GB', 'CH', 'NO', 'CA', 'AU', 'JP', 'KR', 'IN', 'BR',
    'MX', 'SG', 'HK', 'AE', 'SA', 'IL', 'NZ', 'ZA', 'TR', 'UA'
]

# Standard withholding tax rates by category
WITHHOLDING_TAX_RATES = {
    'services': 15.0,       # Standard rate for professional services
    'royalties': 10.0,      # Intellectual property, licenses
    'interest': 10.0,       # Interest payments
    'dividends': 15.0,      # Dividend payments
    'rental': 20.0,         # Rental income from immovable property
}

# VAT Reduced rates for specific categories (EU common patterns)
VAT_REDUCED_RATES = {
    'books': 5.0,
    'food': 10.0,
    'medical': 0.0,
    'education': 0.0,
    'transport': 10.0,
}

# Service categories for VAT treatment
SERVICE_CATEGORIES = {
    'b2b_standard': 'B2B services - reverse charge applies',
    'b2b_digital': 'Digital services B2B - place of supply rules',
    'b2c_standard': 'B2C services - local VAT applies',
    'b2c_digital': 'Digital services B2C - OSS/IOSS rules',
    'exempt': 'VAT exempt services',
}

# GDPR-related constants
GDPR_CONSENT_TYPES = [
    'data_processing',
    'marketing',
    'profiling',
    'data_transfer',
    'third_party_sharing',
]

GDPR_DATA_RETENTION_PERIODS = {
    'contracts': 7,         # Years to retain contract data
    'payments': 10,         # Years to retain payment data (tax purposes)
    'personal_data': 3,     # Years after last activity
    'communication': 2,     # Years to retain communications
}

# Currency formatting
CURRENCY_SYMBOLS = {
    'EUR': '€',
    'USD': '$',
    'GBP': '£',
    'CHF': 'CHF',
    'SEK': 'kr',
    'DKK': 'kr',
    'NOK': 'kr',
    'PLN': 'zł',
    'CZK': 'Kč',
    'HUF': 'Ft',
    'RON': 'lei',
    'BGN': 'лв',
}


def get_vat_rate(country_code: str) -> float:
    """
    Get the standard VAT rate for an EU country.
    
    Args:
        country_code: ISO 2-letter country code
        
    Returns:
        VAT rate as percentage, or 0 if country not found
    """
    country = EU_COUNTRIES.get(country_code.upper())
    return country['vat_rate'] if country else 0.0


def get_country_name(country_code: str) -> str:
    """
    Get the full name of an EU country.
    
    Args:
        country_code: ISO 2-letter country code
        
    Returns:
        Country name or empty string if not found
    """
    country = EU_COUNTRIES.get(country_code.upper())
    return country['name'] if country else ''


def is_eu_country(country_code: str) -> bool:
    """
    Check if a country is an EU member state.
    
    Args:
        country_code: ISO 2-letter country code
        
    Returns:
        True if country is in EU
    """
    return country_code.upper() in EU_COUNTRIES


def is_eurozone_country(country_code: str) -> bool:
    """
    Check if a country is in the Eurozone.
    
    Args:
        country_code: ISO 2-letter country code
        
    Returns:
        True if country uses EUR
    """
    return country_code.upper() in EUROZONE_COUNTRIES


def get_country_currency(country_code: str) -> str:
    """
    Get the main currency for a country.
    
    Args:
        country_code: ISO 2-letter country code
        
    Returns:
        Currency code or 'EUR' as default
    """
    country = EU_COUNTRIES.get(country_code.upper())
    return country['currency'] if country else 'EUR'


def get_retention_period(data_type: str) -> int:
    """
    Get the GDPR data retention period for a data type.
    
    Args:
        data_type: Type of data (contracts, payments, personal_data, communication)
        
    Returns:
        Retention period in years
    """
    return GDPR_DATA_RETENTION_PERIODS.get(data_type, 3)
