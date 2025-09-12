# -*- coding: utf-8 -*-
{
    "name": "Serial Printer — Custom Wizard",
    "summary": "Personalización de productos en eCommerce",
    "version": "18.0.1.0.0",
    "category": "Website/Commerce",
    "author": "Serial Printer",
    "license": "LGPL-3",
    "depends": ["website", "website_sale", "product"],
    "data": [
        "views/product_personalize_button.xml",
        "views/customizer_page.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_custom_wizard/static/src/css/spw.css",
            "serial_printer_custom_wizard/static/src/js/personalize_btn.js",
            "serial_printer_custom_wizard/static/src/js/customizer.js",
            "serial_printer_custom_wizard/static/src/js/spw.js"
        ],
    },
    "installable": True,
    "application": False,
}