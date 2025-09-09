# -*- coding: utf-8 -*-
{
    'name': 'Serial Printer Custom Wizard',
    'version': '1.0',
    'category': 'Website',
    'summary': 'Formulario web para personalización de productos',
    'description': 'Permite al cliente subir logo y elegir técnica, posición, tamaño, color y observaciones.',
    'author': 'Serial Printer Fuerteventura',
    'website': 'https://serial-printer.com',
    'depends': ['website', 'website_sale', 'sale', 'portal', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/personalizacion_wizard_views.xml',
        'views/website_customize_template.xml',
        'views/website_customize_button.xml',
    ],
    'installable': True,
    'application': True,
}