# -*- coding: utf-8 -*-
{
    "name": "Serial Printer - Web Custom",
    "version": "18.0.1.0",
    "category": "Website",
    "summary": "Grid color x talla en ficha producto (estable, sin duplicados).",
    "depends": ["website_sale", "web"],
    "data": [
        # Por ahora SIN vistas XML para evitar xpaths frágiles
        # Si más adelante necesitamos ancla server-side, lo añadimos.
    ],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_web_custom/static/src/js/product_matrix.js",
            "serial_printer_web_custom/static/src/scss/product_matrix.scss",
        ],
    },
    "license": "LGPL-3",
}