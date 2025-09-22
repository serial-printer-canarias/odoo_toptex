# -*- coding: utf-8 -*-
{
    "name": "Serial Printer Web Custom",
    "version": "18.0.1.0.0",
    "category": "Website",
    "summary": "Product matrix (color x talla) con imagen, stock, precio y añadir múltiple al carrito",
    "depends": ["website_sale", "stock"],
    "data": [
        "views/sp_matrix_anchor.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_web_custom/static/src/js/product_matrix.js",
            "serial_printer_web_custom/static/src/scss/product_matrix.scss",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
}