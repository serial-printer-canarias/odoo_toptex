{
    "name": "Personalización de productos Serial Printer",
    "version": "1.0",
    "summary": "Permite a los clientes personalizar productos tras la compra",
    "description": """
        Este módulo permite la personalización post-venta de productos,
        así como una opción pública de personalización previa a la compra para captar leads.
    """,
    "category": "Website",
    "author": "Serial Printer Canarias",
    "website": "https://serial-printer.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "sale",
        "website_sale",
        "portal"
    ],
    "data": [
        "views/personalizacion_wizard_views.xml",
        "views/website_customize_template.xml"
    ],
    "installable": True,
    "application": False,
    "auto_install": False
}