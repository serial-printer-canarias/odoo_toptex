{
    'name': 'Serial Printer Custom Wizard',
    'version': '1.0.0',
    'category': 'Sales',
    'summary': 'Wizard de personalización post-venta y preventa de productos textiles',
    'author': 'Serial Printer',
    'website': 'https://serial-printer.com',
    'license': 'LGPL-3',
    'depends': ['sale', 'website_sale', 'portal', 'crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/personalization_wizard_views.xml',
        'views/website_customize_template.xml',
        'report/mockup_personalization_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            '/serial_printer_custom_wizard/static/src/js/personalization.js',
            '/serial_printer_custom_wizard/static/src/css/style.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}