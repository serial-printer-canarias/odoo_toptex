# -*- coding: utf-8 -*-
{
    'name': 'Serial Printer - Custom Wizard',
    'version': '0.2.0',  # <-- sube versión en cada cambio de assets
    'category': 'Website/Website',
    'summary': 'Botón Personalizar y página de personalización',
    'author': 'Serial Printer',
    'license': 'OEEL-1',
    'depends': ['website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/personalizacion_wizard_views.xml',
        'views/personalizacion_wizard_website_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'serial_printer_custom_wizard/static/src/js/add_customize_button.js',
        ],
    },
    'installable': True,
    'application': False,
}