{
    "name": "Serial Printer Web Custom",
    "version": "18.0.1.0.1",
    "category": "Website",
    "summary": "Product matrix (color x talla) con precio/stock",
    "license": "LGPL-3",
    "depends": ["website_sale"],
    "data": [],
    "assets": {
        # Algunas páginas usan el bundle minimal → incluimos ambos
        "web.assets_frontend_minimal": [
            "serial_printer_web_custom/static/src/js/product_matrix.js",
            "serial_printer_web_custom/static/src/scss/product_matrix.scss",
        ],
        "web.assets_frontend": [
            "serial_printer_web_custom/static/src/js/product_matrix.js",
            "serial_printer_web_custom/static/src/scss/product_matrix.scss",
        ],
    },
}