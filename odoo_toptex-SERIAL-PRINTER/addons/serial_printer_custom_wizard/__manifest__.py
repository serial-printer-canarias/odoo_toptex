{
    'name': 'Serial Printer Custom Wizard',
    'summary': 'Personalización de productos en la web con previsualización',
    'version': '1.0.1',
    'category': 'Website',
    'license': 'LGPL-3',
    'author': 'Serial Printer Fuerteventura',
    'website': 'https://serial-printer.com',
    'depends': ['website', 'website_sale', 'sale', 'portal'],
    'data': [
        'views/personalizacion_wizard_website_views.xml'
    ],
    'assets': {
        'web.assets_frontend': [
            'serial_printer_custom_wizard/static/src/js/add_customize_button.js',
            'serial_printer_custom_wizard/static/src/js/personalizar_preview.js',
            'serial_printer_custom_wizard/static/src/js/personalizar_meta_patch.js',
            'serial_printer_custom_wizard/static/src/css/personalizar_preview.css'
        ]
    },
    'installable': True,
    'application': False
}