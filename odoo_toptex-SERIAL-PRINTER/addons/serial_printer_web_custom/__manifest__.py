# -*- coding: utf-8 -*-
{
    "name": "Serial Printer – Product Matrix (Web)",
    "version": "18.0.1.0.0",
    "category": "Website/Website",
    "summary": "Matriz de cantidades por color/talla en la ficha de producto",
    "license": "LGPL-3",
    "author": "Serial Printer",
    "depends": ["website_sale"],
    "data": [],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_web_custom/static/src/js/product_matrix.js",
            "serial_printer_web_custom/static/src/scss/product_matrix.scss",
        ],
    },
    "installable": True,
    "application": False,
}