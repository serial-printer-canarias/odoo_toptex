# -*- coding: utf-8 -*-
{
    "name": "Serial Printer – Product Matrix (Odoo 18)",
    "summary": "Grid de cantidades por Color/Talla en la ficha de producto",
    "version": "18.0.1.0.0",
    "author": "Serial Printer",
    "license": "LGPL-3",
    "website": "",
    "category": "Website/Website",
    "depends": ["website_sale"],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_web_custom/static/src/js/product_matrix.esm.js",
            "serial_printer_web_custom/static/src/scss/product_matrix.scss",
        ],
    },
    # IMPORTANTE: sin 'data' para evitar errores de xpath en el update
    "installable": True,
    "application": False,
}