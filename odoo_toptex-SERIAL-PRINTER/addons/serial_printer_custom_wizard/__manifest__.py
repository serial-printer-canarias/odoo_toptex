# -*- coding: utf-8 -*-
{
    'name': 'Personalización de productos (Serial Printer)',
    'version': '1.0',
    'summary': 'Formulario web de personalización + botón en producto',
    'category': 'Website',
    'author': 'Serial Printer Fuerteventura',
    'website': 'https://serial-printer.com',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'website_sale',
        'sale',
        'portal',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/personalizacion_views.xml',
        'views/website_customize_button.xml',
        'views/website_customize_template.xml',
    ],
    'assets': {},
    'installable': True,
    'application': False,
}