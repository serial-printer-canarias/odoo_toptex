# addons/serial_printer_custom_wizard/__manifest__.py
{
    "name": "Serial Printer – Custom Wizard",
    "summary": "Personalización de productos en eCommerce",
    "version": "18.0.1.0.0",
    "category": "Website/Commerce",
    "author": "Serial Printer",
    "license": "LGPL-3",
    "depends": [
        "website",
        "website_sale",
    ],
    "data": [
        # Páginas / vistas propias (SIN assets y SIN el heredado del add_to_cart)
        "views/customizer_page.xml",
        "views/personalizacion_form.xml",
        "views/personalizacion_wizard_views.xml",
        "views/personalizacion_wizard_website_views.xml",
        # NO: "views/assets.xml"
        # NO: "views/website_customize_button.xml"  (lo hacemos por JS)
    ],
    "assets": {
        # Estos bundles siempre existen y cargan en el frontend del website
        "web.assets_frontend": [
            "serial_printer_custom_wizard/static/src/js/add_customize_button.js",
            "serial_printer_custom_wizard/static/src/js/customizer_preview.js",
            "serial_printer_custom_wizard/static/src/css/spw.css",
        ],
    },
    "installable": True,
    "application": False,
}