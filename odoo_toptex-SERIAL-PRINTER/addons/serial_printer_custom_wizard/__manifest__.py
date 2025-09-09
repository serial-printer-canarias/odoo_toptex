# -*- coding: utf-8 -*-
{
    'name': 'Serial Printer Custom Wizard',
    'version': '1.0',
    'category': 'Website',
    'summary': 'Formulario de personalización post-venta y público',
    'description': '''
        Permite al cliente subir logo, elegir técnica (serigrafía, bordado, DTF, ninguna), 
        posición del diseño, color, tamaño, y observaciones, tanto tras la compra como antes.
        Genera un PDF para el taller y guarda la información en el portal del cliente.
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
        'views/website_customize_template.xml',   # Formulario web público
        'views/website_customize_button.xml',     # Botón en la ficha de producto
        'views/personalizacion_wizard_views.xml', # Vista backoffice (opcional)
    ],
    'assets': {
        'web.assets_frontend': [
            # Puedes añadir CSS/JS si hace falta para mejorar el wizard
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}