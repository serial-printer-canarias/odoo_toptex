# -*- coding: utf-8 -*-
{
    "name": "Serial Printer – Custom Wizard (mínimo)",
    "version": "16.0.1.0.0",
    "category": "Website/Website",
    "summary": "Botón 'Personalizar' en la ficha de producto + página dummy",
    "depends": ["website_sale"],
    "data": [
        "views/website_templates.xml",
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