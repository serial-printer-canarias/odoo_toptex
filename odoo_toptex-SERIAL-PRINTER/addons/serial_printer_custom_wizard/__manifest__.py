{
    'name': 'Serial Printer Personalización',
    'version': '1.0',
    'summary': 'Permite a los clientes personalizar productos con técnicas como serigrafía, bordado o DTF.',
    'description': """
        Módulo para la gestión de personalizaciones post-venta en productos.
        Incluye selección de técnica, posición, tamaño, colores e impresión del logo.
    """,
    'category': 'Sales',
    'author': 'Serial Printer Canarias',
    'license': 'LGPL-3',
    'depends': ['base', 'product', 'website', 'sale'],
    'data': [
        'views/personalizacion_form.xml',
        # Añade aquí más vistas o acciones si vas creando nuevas
    ],
    'assets': {
        'web.assets_frontend': [
            # Aquí irán los JS/CSS para la web pública si decides añadir wizard web
        ],
    },
    'installable': True,
    'application': True,
}