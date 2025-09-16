{
    "name": "Serial Printer Web Custom",
    "version": "18.0.1.0.0",
    "category": "Website",
    "summary": "Matriz de tallas en ficha de producto del eCommerce",
    "author": "Serial Printer",
    "license": "LGPL-3",
    "depends": ["website_sale"],
    "data": [],
    "assets": {
        # Cargamos en el frontend de Website
        "website.assets_frontend": [
            "serial_printer_web_custom/static/src/js/product_matrix.js",
            "serial_printer_web_custom/static/src/css/product_matrix.css",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}