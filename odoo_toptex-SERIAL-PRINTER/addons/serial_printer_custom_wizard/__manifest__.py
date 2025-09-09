{
    'name': 'Serial Printer Custom Wizard',
    'version': '1.1.2',
    'summary': 'Botón “Personalizar” en la ficha de producto',
    'category': 'Website/Shop',
    'author': 'Serial Printer Fuerteventura',
    'website': 'https://serial-printer.com',
    'license': 'LGPL-3',
    'depends': ['base', 'product', 'website', 'website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',                           # << fuerza el JS
        'views/personalizacion_wizard_website_views.xml',
    ],
    'installable': True,
    'application': False,
}