# -*- coding: utf-8 -*-
{
    "name": "Serial Printer – Custom Wizard",
    "summary": "Añade el botón 'Personalizar' en la ficha de producto y enlaza al personalizador.",
    "version": "1.0.0",
    "category": "Website/Website",
    "depends": ["website_sale"],
    "data": [],                       # SIN XML
    "assets": {
        "web.assets_frontend": [
            "serial_printer_custom_wizard/static/src/js/add_customize_button.js",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}