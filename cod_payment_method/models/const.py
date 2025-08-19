# -*- coding: utf-8 -*-

# Default payment method codes including COD
DEFAULT_PAYMENT_METHOD_CODES = ['cod']

# COD specific constants
COD_FEE_TYPES = [
    ('fixed', 'Fixed Amount'),
    ('percent', 'Percentage')
]

# Default COD countries (Middle East region)
DEFAULT_COD_COUNTRIES = [
    'EG',  # Egypt
    'SA',  # Saudi Arabia
    'AE',  # UAE
    'KW',  # Kuwait
    'QA',  # Qatar
    'BH',  # Bahrain
    'OM',  # Oman
    'JO',  # Jordan
    'LB',  # Lebanon
    'IQ',  # Iraq
    'SY',  # Syria
    'YE',  # Yemen
    'PS',  # Palestine
    'LY',  # Libya
    'TN',  # Tunisia
    'DZ',  # Algeria
    'MA',  # Morocco
    'SD',  # Sudan
]

# COD order states where fee can be modified
COD_EDITABLE_STATES = ['draft', 'sent']

# Maximum percentage for COD fee
MAX_COD_FEE_PERCENT = 10.0

# Minimum order amount for COD (default)
DEFAULT_MIN_COD_AMOUNT = 0.0

# Maximum order amount for COD (default, 0 means no limit)
DEFAULT_MAX_COD_AMOUNT = 0.0
