# Copyright (c) 2024, HRMS Freelancer and contributors
# For license information, please see license.txt

"""
HRMS Freelancer utilities package
"""

from hrms_freelancer.utils.currency import (
    get_exchange_rate,
    convert_currency,
    format_currency_amount,
    update_exchange_rates_from_api,
    get_all_exchange_rates
)

from hrms_freelancer.utils.tax_calculations import (
    TaxCalculator,
    calculate_freelancer_taxes,
    estimate_annual_tax_burden,
    get_tax_year_dates,
    validate_tax_id
)

from hrms_freelancer.utils.constants import (
    EU_COUNTRIES,
    EU_COUNTRY_CODES,
    EU_COUNTRY_NAMES,
    EUROZONE_COUNTRIES,
    NON_EUROZONE_EU_COUNTRIES,
    TREATY_COUNTRIES,
    WITHHOLDING_TAX_RATES,
    VAT_REDUCED_RATES,
    SERVICE_CATEGORIES,
    GDPR_CONSENT_TYPES,
    GDPR_DATA_RETENTION_PERIODS,
    CURRENCY_SYMBOLS,
    get_vat_rate,
    get_country_name,
    is_eu_country,
    is_eurozone_country,
    get_country_currency,
    get_retention_period
)

__all__ = [
    # Currency utilities
    "get_exchange_rate",
    "convert_currency",
    "format_currency_amount",
    "update_exchange_rates_from_api",
    "get_all_exchange_rates",
    
    # Tax utilities
    "TaxCalculator",
    "calculate_freelancer_taxes",
    "estimate_annual_tax_burden",
    "get_tax_year_dates",
    "validate_tax_id",
    
    # Constants
    "EU_COUNTRIES",
    "EU_COUNTRY_CODES",
    "EU_COUNTRY_NAMES",
    "EUROZONE_COUNTRIES",
    "NON_EUROZONE_EU_COUNTRIES",
    "TREATY_COUNTRIES",
    "WITHHOLDING_TAX_RATES",
    "VAT_REDUCED_RATES",
    "SERVICE_CATEGORIES",
    "GDPR_CONSENT_TYPES",
    "GDPR_DATA_RETENTION_PERIODS",
    "CURRENCY_SYMBOLS",
    "get_vat_rate",
    "get_country_name",
    "is_eu_country",
    "is_eurozone_country",
    "get_country_currency",
    "get_retention_period"
]
