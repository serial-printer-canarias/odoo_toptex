{
    'name': 'Personalización de productos Serial Printer',
    'version': '1.0',
    'summary': 'Formulario de personalización para pedidos y clientes',
    'description': '''
        Este módulo permite a los clientes personalizar productos después de realizar un pedido,
        así como acceder a un personalizador público para captación de leads.
    ''',
    'category': 'Website',
    'author': 'Serial Printer Canarias',
    'website': 'https://serial-printer.com',
    'license': 'LGPL-3',
    'depends': ['base', 'sale', 'website_sale', 'portal'],
    'data': [
        'views/personalizacion_wizard_views.xml',
        'views/website_customize_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            # Aquí puedes incluir JS/CSS si lo necesitas
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}