# -*- coding: utf-8 -*-
{
    "name": "Serial Printer – Custom Wizard",
    "summary": "Botón 'Personalizar' en la ficha de producto y enlace al personalizador.",
    "version": "1.0.0",              # <- formato x.y.z que tu instancia acepta
    "category": "Website/Website",
    "depends": ["website_sale"],
    "data": [
        "views/website_customize_button.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_custom_wizard/static/src/js/add_customize_button.js",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}