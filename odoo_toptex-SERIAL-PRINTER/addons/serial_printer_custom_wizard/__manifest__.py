{
    'name': 'Serial Printer Custom Wizard',
    'version': '16.0.1.0.0',
    'summary': 'Formulario de personalización de productos (web + backend)',
    'description': '''
Permite al cliente subir logo y elegir técnica, posición, tamaño y color.
Guarda una solicitud de personalización vinculada al producto.
Incluye vista pública sencilla para enviar la solicitud.
''',
    'author': 'Serial Printer Fuerteventura',
    'website': 'https://serial-printer.com',
    'category': 'Website',
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
        'views/website_customize_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            # (si luego quieres CSS/JS, se añade aquí)
        ],
    },
    'installable': True,
    'application': True,
}