# -*- coding: utf-8 -*-
{
    "name": "Serial Printer Web Custom",
    "version": "18.0.1.0.0",
    "category": "Website/Website",
    "summary": "Matriz de cantidades por color/talla en la página de producto",
    "depends": ["website_sale"],
    "data": [
        "views/sp_matrix_anchor.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_web_custom/static/src/scss/product_matrix.scss",
            "serial_printer_web_custom/static/src/js/product_matrix.js",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}