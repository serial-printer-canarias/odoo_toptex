{
    "name": "Serial Printer – Customize button",
    "version": "17.0.1.0.0",   # <- semver válido
    "summary": "Añade el botón «Personalizar» en la página de producto.",
    "category": "Website/Website",
    "author": "Serial Printer",
    "license": "LGPL-3",
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