{
    'name': 'Serial Printer Custom Wizard',
    'version': '1.0',
    'category': 'Website',
    'summary': 'Formulario de personalización de productos',
    'description': '''
        Permite al cliente subir logo, elegir técnica de impresión, 
        posición del diseño, color, tamaño, etc.
        Genera un PDF para el taller y guarda los datos en el portal del cliente.
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
        'views/website_customize_template.xml',
        'views/website_customize_button.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            # Puedes añadir CSS/JS si hace falta
        ],
    },
    'installable': True,
    'application': True,
}