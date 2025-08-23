{
    'name': 'Custody Request',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Simple Custody Request Management',
    'description': """
        Simple module for managing custody requests with dynamic approval workflow
    """,
    'depends': ['base',  'mail' , 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'security/custody_security.xml',
        'data/sequence_data.xml',
        'views/approval_config_views.xml',
        'views/custody_request_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,

}