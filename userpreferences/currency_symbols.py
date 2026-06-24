"""
Currency Symbol Mapping Module

Maps ISO 4217 currency codes to their corresponding symbols.
This is the single source of truth for currency symbols across the entire project.
No hardcoded symbols anywhere in templates or serializers.
"""

# Currency code to symbol mapping
# Source: ISO 4217 currency codes
CURRENCY_SYMBOLS = {
    'AED': 'د.إ',
    'AFN': '؋',
    'ALL': 'L',
    'AMD': '֏',
    'ANG': 'ƒ',
    'AOA': 'Kz',
    'ARS': '$',
    'AUD': 'A$',
    'AWG': 'ƒ',
    'AZN': '₼',
    'BAM': 'KM',
    'BBD': '$',
    'BDT': '৳',
    'BGN': 'лв',
    'BHD': '.د.ب',
    'BIF': 'FBu',
    'BMD': '$',
    'BND': '$',
    'BOB': 'Bs.',
    'BRL': 'R$',
    'BSD': '$',
    'BTC': '₿',
    'BTN': 'Nu.',
    'BWP': 'P',
    'BYN': 'Br',
    'BZD': '$',
    'CAD': 'C$',
    'CDF': 'FC',
    'CHF': 'CHF',
    'CLF': 'UF',
    'CLP': '$',
    'CNH': '¥',
    'CNY': '¥',
    'COP': '$',
    'CRC': '₡',
    'CUC': '$',
    'CUP': '$',
    'CVE': '$',
    'CZK': 'Kč',
    'DJF': 'Fdj',
    'DKK': 'kr',
    'DOP': '$',
    'DZD': 'د.ج',
    'EGP': '£',
    'ERN': 'Nfk',
    'ETB': 'Br',
    'EUR': '€',
    'FJD': '$',
    'FKP': '£',
    'GBP': '£',
    'GEL': '₾',
    'GHP': 'GH₵',
    'GIP': '£',
    'GMD': 'D',
    'GNF': 'FG',
    'GTQ': 'Q',
    'GYD': '$',
    'HKD': 'HK$',
    'HNL': 'L',
    'HRK': 'kn',
    'HTG': 'G',
    'HUF': 'Ft',
    'IDR': 'Rp',
    'ILS': '₪',
    'INR': '₹',
    'IQD': 'ع.د',
    'IRR': '﷼',
    'ISK': 'kr',
    'JEP': '£',
    'JMD': '$',
    'JOD': 'د.ا',
    'JPY': '¥',
    'KES': 'KSh',
    'KGS': 'лв',
    'KHR': '៛',
    'KMF': 'CF',
    'KPW': '₩',
    'KRW': '₩',
    'KWD': 'د.ك',
    'KYD': '$',
    'KZT': '₸',
    'LAK': '₭',
    'LBP': 'ل.ل',
    'LKR': 'Rs',
    'LRD': '$',
    'LSL': 'L',
    'LYD': 'ل.د',
    'MAD': 'د.م.',
    'MDL': 'L',
    'MGA': 'Ar',
    'MKD': 'ден',
    'MMK': 'K',
    'MNT': '₮',
    'MOP': 'MOP$',
    'MRU': 'UM',
    'MUR': '₨',
    'MVR': 'Rf',
    'MWK': 'MK',
    'MXN': '$',
    'MYR': 'RM',
    'MZN': 'MT',
    'NAD': '$',
    'NGN': '₦',
    'NIO': 'C$',
    'NOK': 'kr',
    'NPR': '₨',
    'NZD': '$',
    'OMR': 'ر.ع.',
    'PAB': 'B/.',
    'PEN': 'S/',
    'PGK': 'K',
    'PHP': '₱',
    'PKR': '₨',
    'PLN': 'zł',
    'PYG': '₲',
    'QAR': 'ر.ق',
    'RON': 'lei',
    'RSD': 'дин.',
    'RUB': '₽',
    'RWF': 'FRw',
    'SAR': 'ر.س',
    'SBD': '$',
    'SCR': '₨',
    'SDG': 'ج.س.',
    'SEK': 'kr',
    'SGD': '$',
    'SHP': '£',
    'SLL': 'Le',
    'SOS': 'Sh',
    'SRD': '$',
    'SSP': '£',
    'STN': 'Db',
    'SYP': '£',
    'SZL': 'L',
    'THB': '฿',
    'TJS': 'SM',
    'TMT': 'm',
    'TND': 'د.ت',
    'TOP': 'T$',
    'TRY': '₺',
    'TTD': '$',
    'TWD': 'NT$',
    'TZS': 'TSh',
    'UAH': '₴',
    'UGX': 'USh',
    'USD': '$',
    'UYU': '$',
    'UZS': 'лв',
    'VEF': 'Bs.',
    'VND': '₫',
    'VUV': 'VT',
    'WST': 'T',
    'XAF': 'FCFA',
    'XAG': 'Ag',
    'XAU': 'Au',
    'XCD': '$',
    'XDR': 'SDR',
    'XOF': 'CFA',
    'XPD': 'Pd',
    'XPF': '₣',
    'XPT': 'Pt',
    'YER': '﷼',
    'ZAR': 'R',
    'ZMW': 'ZK',
    'ZWL': '$',
}

# Default currency when user has not set any preference
DEFAULT_CURRENCY = 'USD'

# Default currency symbol for fallback
DEFAULT_SYMBOL = '$'


def get_currency_symbol(currency_code: str) -> str:
    """
    Get the symbol for a given currency code.
    
    Args:
        currency_code: ISO 4217 currency code (e.g., 'USD', 'EUR', 'INR')
    
    Returns:
        Currency symbol, or '$' if not found
    """
    return CURRENCY_SYMBOLS.get(currency_code.upper(), DEFAULT_SYMBOL)


def get_all_currencies():
    """
    Get all supported currencies with their codes and symbols.
    
    Returns:
        List of tuples: [(code, symbol, name), ...]
    """
    return [
        (code, symbol) 
        for code, symbol in CURRENCY_SYMBOLS.items()
    ]
