{
    'name': 'Asistente de Personalización Serial Printer',
    'version': '1.0',
    'summary': 'Permite a los clientes personalizar productos después de la compra o como herramienta de marketing.',
    'description': """
Este módulo permite a los clientes de Serial Printer:
- Subir un logo para personalización.
- Elegir técnica (serigrafía, bordado, DTF o ninguna).
- Seleccionar posición del diseño (frontal o espalda).
- Elegir tamaño y color de impresión.
- Añadir observaciones.
Además, incluye:
- Vista pública para captar clientes nuevos desde la web.
- Generación de mockups y PDF para taller.
""",
    'author': 'Serial Printer Canarias',
    'website': 'https://www.serial-printer.com',
    'category': 'Website',
    'depends': ['sale', 'website_sale', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'views/personalizacion_wizard_views.xml',
        'views/website_customize_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            # Añadir aquí JS o CSS si lo usas
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}