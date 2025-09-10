# -*- coding: utf-8 -*-
{
    "name": "Serial Printer – Custom Wizard",
    "summary": "Botón 'Personalizar' en la ficha de producto y enlace al personalizador.",
    "version": "17.0.1",  # <- formato x.y.z para evitar el error del log
    "category": "Website/Website",
    "depends": ["website_sale"],
    "data": [
        "views/website_customize_button.xml",  # plantilla “dummy” (no rompe nada)
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