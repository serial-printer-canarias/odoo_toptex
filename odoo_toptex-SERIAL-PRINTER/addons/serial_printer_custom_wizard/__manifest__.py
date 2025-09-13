# -*- coding: utf-8 -*-
{
    "name": "Serial Printer - Custom Wizard",
    "version": "18.0.1.0",
    "author": "Serial Printer",
    "license": "LGPL-3",
    "depends": ["website_sale"],
    "data": [
        "views/product_button.xml",
        "views/customizer_page.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_custom_wizard/static/src/js/spw_button.js",
            "serial_printer_custom_wizard/static/src/js/spw.js",
            "serial_printer_custom_wizard/static/src/css/spw.css",
        ],
    },
    "installable": True,
    "application": False,
}