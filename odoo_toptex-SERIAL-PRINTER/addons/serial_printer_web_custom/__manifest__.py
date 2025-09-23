# -*- coding: utf-8 -*-
{
    "name": "Serial Printer Web Custom",
    "version": "18.0.0.7",
    "summary": "Matriz de variantes en la página de producto",
    "category": "Website",
    "license": "LGPL-3",
    "depends": ["website_sale"],
    "data": [
        "views/sp_matrix_anchor.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_web_custom/static/src/js/product_matrix.js",
            "serial_printer_web_custom/static/src/scss/product_matrix.scss",
        ],
    },
    "installable": True,
    "application": False,
}