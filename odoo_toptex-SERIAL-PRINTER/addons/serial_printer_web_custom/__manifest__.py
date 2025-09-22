# -*- coding: utf-8 -*-
{
    "name": "Serial Printer Web Custom",
    "version": "18.0.1.0.0",
    "category": "Website",
    "summary": "Product matrix (color x talla) con precio/stock",
    "depends": ["website_sale"],
    "data": [],
    "assets": {
        # Algunas vistas de producto cargan este bundle
        "web.assets_frontend": [
            "serial_printer_web_custom/static/src/js/product_matrix.js",
            "serial_printer_web_custom/static/src/scss/product_matrix.scss",
        ],
        # Otras vistas (themes/plantillas) cargan este otro
        "website.assets_frontend": [
            "serial_printer_web_custom/static/src/js/product_matrix.js",
            "serial_printer_web_custom/static/src/scss/product_matrix.scss",
        ],
    },
    "license": "LGPL-3",
}