# -*- coding: utf-8 -*-
# Part of AlmightyCS. See LICENSE file for full copyright and licensing details.
#╔══════════════════════════════════════════════════════════════════════╗
#║                                                                      ║
#║                  ╔═══╦╗       ╔╗  ╔╗     ╔═══╦═══╗                   ║
#║                  ║╔═╗║║       ║║ ╔╝╚╗    ║╔═╗║╔═╗║                   ║
#║                  ║║ ║║║╔╗╔╦╦══╣╚═╬╗╔╬╗ ╔╗║║ ╚╣╚══╗                   ║
#║                  ║╚═╝║║║╚╝╠╣╔╗║╔╗║║║║║ ║║║║ ╔╬══╗║                   ║
#║                  ║╔═╗║╚╣║║║║╚╝║║║║║╚╣╚═╝║║╚═╝║╚═╝║                   ║
#║                  ╚╝ ╚╩═╩╩╩╩╩═╗╠╝╚╝╚═╩═╗╔╝╚═══╩═══╝                   ║
#║                            ╔═╝║     ╔═╝║                             ║
#║                            ╚══╝     ╚══╝                             ║
#║                  SOFTWARE DEVELOPED AND SUPPORTED BY                 ║
#║                ALMIGHTY CONSULTING SOLUTIONS PVT. LTD.               ║
#║                      COPYRIGHT (C) 2016 - TODAY                      ║
#║                      https://www.almightycs.com                      ║
#║                                                                      ║
#╚══════════════════════════════════════════════════════════════════════╝
{
    "name": "ACS HMS Dashboards", 
    "summary": "HMS Dashboard for users. Separate dashboard details for doctor, receptionist and admin user so they can get their related information and statistics from single view",
    "description": """HMS Dashboard for users. Separate dashboard details for doctor, receptionist and admin user so they can get their related information and statistics from single view.
        Hospital Management System hospital dashboard physician dashboard admin dashboard ACS HMS
    """, 
    'version': '1.2.14',
    'category': 'Medical',
    'author': 'Almighty Consulting Solutions Pvt. Ltd.',
    'support': 'info@almightycs.com',
    'website': 'https://www.almightycs.com',
    'license': 'OPL-1',
    "depends": ["acs_hms",'web'],
    "data": [
        "security/security.xml",
        'security/ir.model.access.csv',
        "views/acs_hms_dashboard_view.xml",
        "views/user_view.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'acs_hms_dashboard/static/src/lib/js/core.js',
            'acs_hms_dashboard/static/src/lib/js/charts.js',
            'acs_hms_dashboard/static/src/lib/js/animated.js',
            'acs_hms_dashboard/static/src/lib/js/index.js',
            'acs_hms_dashboard/static/src/lib/js/apexcharts.js',
            'acs_hms_dashboard/static/src/css/*.css',
            'acs_hms_dashboard/static/src/components/*.js',
            'acs_hms_dashboard/static/src/components/acs_hms_dashboard.xml',
        ],
    },
    'images': [
        'static/description/acs_hms_dashboard_almightycs_odoo_cover.gif',
    ],
    'cloc_exclude': [
        "static/src/lib/**/*", # exclude all files in a folder hierarchy recursively
    ],
    'application': False,
    'sequence': 2,
    'price': 75,
    'currency': 'USD',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: