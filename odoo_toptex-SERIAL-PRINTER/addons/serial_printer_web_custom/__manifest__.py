# -*- coding: utf-8 -*-
{
    "name": "Serial Printer Web Custom",
    "summary": "Rejilla Color x Talla en la ficha de producto (Website)",
    "version": "18.0.1.0.0",
    "category": "Website/Shop",
    "license": "LGPL-3",
    "author": "Serial Printer",
    "depends": ["website_sale"],
    "data": [],  # << NO cargamos vistas para evitar 500; todo va por assets
    "assets": {
        # Frontend (tienda). Si prefieres, puedes dejar solo uno de los dos bundles.
        "web.assets_frontend": [
            "serial_printer_web_custom/static/src/js/product_matrix.js",
            "serial_printer_web_custom/static/src/scss/product_matrix.scss",
        ],
        "website.assets_frontend": [
            "serial_printer_web_custom/static/src/js/product_matrix.js",
            "serial_printer_web_custom/static/src/scss/product_matrix.scss",
        ],
    },
    "installable": True,
    "application": False,
}