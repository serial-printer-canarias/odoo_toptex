# -*- coding: utf-8 -*-
{
    'name': 'Serial Printer Custom Wizard',
    'version': '1.0',
    'category': 'Website',
    'summary': 'Formulario de personalización desde la página de producto',
    'description': 'Añade un botón "Personalizar" en la página de producto y muestra un formulario web.',
    'author': 'Serial Printer Fuerteventura',
    'website': 'https://serial-printer.com',
    'depends': ['website', 'website_sale'],
    'data': [
        # Solo cargamos lo que es seguro y no rompe la instalación
        'views/website_customize_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'serial_printer_custom_wizard/static/src/js/add_customize_button.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}