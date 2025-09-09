{
    'name': 'Serial Printer Custom Wizard',
    'version': '1.1.0',
    'summary': 'Gestión de personalización + botón en eCommerce',
    'category': 'Sales/Customization',
    'author': 'Serial Printer Fuerteventura',
    'website': 'https://serial-printer.com',
    'license': 'LGPL-3',
    'depends': ['base', 'product', 'sale', 'website', 'website_sale'],
    'data': [
        # Backoffice
        'security/ir.model.access.csv',
        'views/personalizacion_wizard_views.xml',
        # Página web muy simple para probar la ruta
        'views/personalizacion_wizard_website_views.xml',
    ],
    'assets': {
        # Solo un JS pequeño que inserta el botón en la ficha de producto
        'web.assets_frontend': [
            'serial_printer_custom_wizard/static/src/js/add_customize_button.js',
        ],
    },
    'installable': True,
    'application': False,
}