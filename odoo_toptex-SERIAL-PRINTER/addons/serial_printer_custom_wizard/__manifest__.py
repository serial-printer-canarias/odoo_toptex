# addons/serial_printer_custom_wizard/__manifest__.py
{
    "name": "Serial Printer - Custom Wizard (Button)",
    "summary": "Añade el botón “Personalizar” en la ficha de producto.",
    "version": "1.0.0",              # semver simple para que no dé error
    "license": "LGPL-3",
    "author": "Serial Printer",
    "depends": ["website_sale"],
    "data": [],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_custom_wizard/static/src/js/add_customize_button.js",
        ],
    },
    "installable": True,
    "application": False,
}