# -*- coding: utf-8 -*-
{
    'name': 'Serial Printer Custom Wizard',
    'version': '1.0',
    'category': 'Website',
    'summary': 'Personalizador sencillo con preview en la web',
    'description': '''
Permite al cliente subir logo, escoger técnica/posición/color, ver una previsualización
sobre la imagen del producto y enviar los datos al carrito / al taller.
''',
    'author': 'Serial Printer Fuerteventura',
    'website': 'https://serial-printer.com',
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
        'views/personalizacion_wizard_website_views.xml',
        'views/website_customize_button.xml',
        'report/mockup_personalizacion_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            # JS del botón en la ficha (si lo estás usando)
            'serial_printer_custom_wizard/static/src/js/add_customize_button.js',
            # NUEVOS assets del previsualizador
            'serial_printer_custom_wizard/static/src/js/customizer_preview.js',
            'serial_printer_custom_wizard/static/src/css/customizer.css',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}