{
    'name': 'Serial Printer Custom Wizard',
    'version': '1.1.1',
    'summary': 'Botón “Personalizar” en ficha de producto + ruta web de prueba',
    'category': 'Sales/Customization',
    'author': 'Serial Printer Fuerteventura',
    'website': 'https://serial-printer.com',
    'license': 'LGPL-3',
    'depends': ['base', 'product', 'sale', 'website', 'website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/personalizacion_wizard_views.xml',
        'views/personalizacion_wizard_website_views.xml',
        'views/assets.xml',  # << forzamos la carga del JS en frontend
    ],
    'installable': True,
    'application': False,
}