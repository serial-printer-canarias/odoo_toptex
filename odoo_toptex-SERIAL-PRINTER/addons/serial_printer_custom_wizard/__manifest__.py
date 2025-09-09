# -*- coding: utf-8 -*-
{
    'name': 'Serial Printer Custom Wizard',
    'version': '1.0.0',
    'category': 'Website',
    'summary': 'Formulario de personalización de productos en website + mockup/report',
    'description': """
Permite al cliente subir logo y elegir técnica, posición, color y cantidad
desde el eCommerce. Registra la personalización y genera un mockup/report.
""",
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
        'views/personalizacion_wizard_views.xml',
        'views/personalizacion_form.xml',
        'views/website_customize_template.xml',
        'report/mockup_personalizacion_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            # Botón de “Personalizar” inyectado por JS (no usa xpath)
            'serial_printer_custom_wizard/static/src/js/add_customize_button.js',
        ],
    },
    'installable': True,
    'application': True,
}