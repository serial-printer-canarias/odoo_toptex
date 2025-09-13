# -*- coding: utf-8 -*-
{
    "name": "Serial Printer — Custom Wizard",
    "summary": "Botón Personalizar + previsualización de logo sobre imagen de la variante (Odoo 18)",
    "version": "18.0.1.0.0",
    "category": "Website/Commerce",
    "author": "Serial Printer",
    "license": "LGPL-3",
    "depends": ["website_sale"],
    "data": [
        "views/product_personalize_button.xml",
        "views/customizer_page.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_custom_wizard/static/src/css/spw.css",
            "serial_printer_custom_wizard/static/src/js/spw.js",
        ],
    },
    "installable": True,
    "application": False,
}