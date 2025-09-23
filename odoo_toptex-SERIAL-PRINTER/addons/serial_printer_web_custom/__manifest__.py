# -*- coding: utf-8 -*-
{
    "name": "Serial Printer – Product Matrix",
    "version": "18.0.0.8",
    "summary": "Matriz de compra por color/talla en la ficha de producto",
    "category": "Website/Website",
    "license": "LGPL-3",
    "depends": ["website_sale", "stock"],
    "data": [
        "views/sp_matrix_anchor.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_web_custom/static/src/scss/product_matrix.scss",
            "serial_printer_web_custom/static/src/js/product_matrix.esm.js",
        ],
    },
    "installable": True,
    "application": False,
}