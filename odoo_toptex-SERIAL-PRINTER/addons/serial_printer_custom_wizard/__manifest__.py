# -*- coding: utf-8 -*-
{
    "name": "Serial Printer - Custom Wizard",
    "version": "18.0.1.0.7",
    "summary": "Personalización de producto con vista previa de logo.",
    "category": "Website/Website",
    "license": "LGPL-3",
    "depends": ["website_sale"],
    "data": [
        "views/customizer_page.xml",
        "views/product_personalize_button.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_custom_wizard/static/src/js/spw_button.js",
        ],
    },
    "installable": True,
    "application": False,
}