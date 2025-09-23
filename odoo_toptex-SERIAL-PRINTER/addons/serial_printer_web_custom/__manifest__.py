# -*- coding: utf-8 -*-
{
    "name": "Serial Printer | Web Custom (Matrix)",
    "version": "18.0.1.0.1",
    "category": "Website/Website",
    "summary": "Product matrix (color/size) on product page",
    "author": "Serial Printer",
    "license": "LGPL-3",
    "depends": ["website_sale"],
    "data": [
        "views/sp_matrix_anchor.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_web_custom/static/src/js/sp_probe.esm.js",
            "serial_printer_web_custom/static/src/js/product_matrix.esm.js",
            "serial_printer_web_custom/static/src/scss/product_matrix.scss",
        ],
    },
    "installable": True,
}