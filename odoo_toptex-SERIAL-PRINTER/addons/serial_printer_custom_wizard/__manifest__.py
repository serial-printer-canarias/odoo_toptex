# -*- coding: utf-8 -*-
{
    'name': 'Serial Printer Custom Wizard',
    'version': '1.0.0',
    'category': 'Website',
    'author': 'Serial Printer Fuerteventura',
    'depends': ['website', 'website_sale', 'sale', 'portal', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        # (de momento SIN vistas para no romper la carga)
    ],
    'assets': {
        'web.assets_frontend': [
            # lo puedes dejar ya, no rompe builds
            'serial_printer_custom_wizard/static/src/js/add_customize_button.js',
        ],
    },
    'installable': True,
    'application': False,
}