{
    "name": "Serial Printer Web Custom",
    "version": "18.0.1.0.0",
    "category": "Website",
    "summary": "Product matrix (color x talla) con precio/stock",
    "depends": ["website_sale"],
    "data": [
        "views/sp_matrix_anchor.xml",   # <-- solo el ancla, nada más
    ],
    "assets": {
        # Lo cargamos en ambos bundles para evitar sorpresas del tema
        "web.assets_frontend": [
            "serial_printer_web_custom/static/src/js/product_matrix.js",
            "serial_printer_web_custom/static/src/scss/product_matrix.scss",
        ],
        "website.assets_wsale": [
            "serial_printer_web_custom/static/src/js/product_matrix.js",
            "serial_printer_web_custom/static/src/scss/product_matrix.scss",
        ],
    },
    "license": "LGPL-3",
}