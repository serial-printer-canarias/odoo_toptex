{
    "name": "Asistente de Personalización de Productos",
    "summary": "Permite a los clientes personalizar productos con logo, técnica y observaciones.",
    "description": """
Este módulo añade un asistente de personalización de productos, permitiendo a los clientes:
- Subir su logo
- Elegir técnica de personalización (serigrafía, bordado, DTF, ninguna)
- Seleccionar el tamaño y color de impresión
- Indicar observaciones
- Visualizar el producto personalizado

Funciona tanto tras la compra como en formato de presupuesto desde la web.
    """,
    "version": "1.0",
    "category": "Personalización",
    "author": "Serial Printer Canarias",
    "website": "https://serial-printer-canarias.odoo.com",
    "license": "AGPL-3",
    "depends": [
        "website",
        "portal",
        "product",
        "sale",
    ],
    "data": [
        "views/personalizacion_wizard_views.xml",
        "views/website_customize_template.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "/serial_printer_custom_wizard/static/src/css/custom_wizard.css",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}