# -*- coding: utf-8 -*-
{
    "name": "Serial Printer — Custom Wizard",
    "version": "16.0.1.0.0",  # usa 17.0.* si tu base es v17
    "category": "Website/Website",
    "summary": "Botón Personalizar + página de previsualización de logo sobre la variante.",
    "license": "LGPL-3",
    "author": "Serial Printer",
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
        "web.assets_frontend_lazy": [
            "serial_printer_custom_wizard/static/src/js/spw.js",
        ],
    },
    "installable": True,
    "application": False,
}