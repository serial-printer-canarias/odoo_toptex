{
    "name": "Serial Printer Custom Wizard",
    "version": "1.2.0",
    "summary": "Botón “Personalizar” en la ficha de producto",
    "category": "Website/Shop",
    "author": "Serial Printer Fuerteventura",
    "website": "https://serial-printer.com",
    "license": "LGPL-3",
    "depends": ["base", "product", "website", "website_sale"],
    "data": [
        "security/ir.model.access.csv",
        "views/personalizacion_wizard_website_views.xml",  # página destino de prueba
    ],
    "assets": {
        # Inyectamos el JS en todos los frontends de web/website
        "web.assets_frontend": [
            "serial_printer_custom_wizard/static/src/js/add_customize_button.js",
        ],
        "website.assets_frontend": [
            "serial_printer_custom_wizard/static/src/js/add_customize_button.js",
        ],
    },
    "installable": True,
    "application": False,
}