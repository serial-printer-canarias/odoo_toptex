# addons/serial_printer_custom_wizard/__manifest__.py
{
    "name": "Serial Printer — Custom Wizard",
    "summary": "Personalización de productos en Website",
    "version": "18.0.1.0.0",
    "category": "Website/Commerce",
    "author": "Serial Printer",
    "license": "LGPL-3",
    "depends": ["website", "website_sale"],
    "data": [
        "views/customizer_page.xml",
        "views/personalizacion_form.xml",
        "views/personalizacion_wizard_views.xml",
        "views/personalizacion_wizard_website_views.xml"
    ],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_custom_wizard/static/src/css/spw.css",
            "serial_printer_custom_wizard/static/src/js/spw.js"
        ]
    },
    "installable": True,
    "application": False
}