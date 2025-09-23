# -*- coding: utf-8 -*-
{
    "name": "Serial Printer Web Custom",
    "version": "18.0.1.1.0",  # súbelo para forzar rebuild de assets
    "category": "Website/Website",
    "summary": "Matriz de cantidades por color/talla en la ficha de producto",
    "depends": ["website_sale"],
    "data": [
        "views/sp_matrix_anchor.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            # ⚠️ rutas relativas SIN barra inicial y con el nombre del módulo
            "serial_printer_web_custom/static/src/js/product_matrix.js",
            "serial_printer_web_custom/static/src/scss/product_matrix.scss",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}