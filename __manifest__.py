# -*- coding: utf-8 -*-
{
    'name': "riders_logistics",

    'summary': """
        This app is developed to mange the day to day logistics for riders for health Nigeria""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Secteur Network Solutions",
    'website': "http://www.secteurnetworks.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'sale_management', 'account', 'purchase', 'board', 'sale', 'website'],

    # always loaded
    'data': [
        'wizard/collection.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/views2.xml',
        'views/templates.xml',
        'data/automation.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
