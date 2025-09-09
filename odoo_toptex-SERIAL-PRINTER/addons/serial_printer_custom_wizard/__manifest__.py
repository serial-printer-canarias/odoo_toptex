# -*- coding: utf-8 -*-
{
    'name': 'Serial Printer Custom Wizard',
    'version': '1.0',
    'category': 'Website',
    'summary': 'Formulario simple de personalización en la web',
    'description': 'Añade un botón en la ficha de producto que abre un formulario web de personalización.',
    'author': 'Serial Printer Fuerteventura',
    'website': 'https://serial-printer.com',
    'depends': [
        'website',
        'website_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/website_customize_button.xml',
        'views/website_customize_template.xml',
    ],
    'assets': {},
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}