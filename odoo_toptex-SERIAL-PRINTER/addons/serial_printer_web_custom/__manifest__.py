# -*- coding: utf-8 -*-
{
    "name": "Serial Printer – Web Custom (Matrix)",
    "version": "18.0.1.0",
    "summary": "Matriz por color/talla con precio, stock, foto y añadir al carrito en lote",
    "author": "Serial Printer",
    "website": "https://serial-printer.example",
    "license": "LGPL-3",
    "depends": ["website_sale"],
    "data": [
        "views/sp_matrix_anchor.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            # Debug seguro para que no vuelva a salir "_sp is not defined"
            "serial_printer_web_custom/static/src/js/sp_probe.esm.js",
            # Matriz
            "serial_printer_web_custom/static/src/js/product_matrix.esm.js",
            "serial_printer_web_custom/static/src/scss/product_matrix.scss",
        ],
    },
    "installable": True,
}