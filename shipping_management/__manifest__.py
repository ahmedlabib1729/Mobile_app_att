# -*- coding: utf-8 -*-
{
    'name': 'Shipping Management System',
    'version': '1.0.0',
    'category': 'Logistics/Shipping',
    'summary': 'نظام إدارة خدمات الشحن والتوصيل المتكامل مع تحليل المنتجات',
    'description': """
        نظام شامل لإدارة عمليات الشحن والتوصيل يتضمن:
        - إدارة طلبات الشحن
        - تحليل المنتجات المشحونة
        - تكامل مع شركات الشحن (Aramex, FedEx, DHL)
        - نظام CRM متكامل للعملاء
        - تقارير وتحليلات متقدمة
        - نظام محاسبي متكامل
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'sale',
        'sale_management',
        'crm',
        'account',
        'stock',
        'website',
        'mail',
        'contacts',
        'product',
    ],
    'data': [
        # Security
        'security/shipping_security.xml',
        'security/ir.model.access.csv',

        # Data

        'data/sequence_data.xml',
        'data/shipping_companies_data.xml',
        'data/product_analysis_server_actions.xml',


        # Views

        'views/shipping_order_views.xml',
        'views/shipping_company_views.xml',
        'views/product_analysis_views.xml',
        'views/customer_profile_views.xml',
        'views/res_partner_views.xml',
        #'views/dashboard_views.xml',
        'views/loyalty_system_views.xml',
        'views/menu_views.xml',


    ],

    'demo': [
        'demo/demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'icon': 'shipping_management/static/description/icon.png',
}