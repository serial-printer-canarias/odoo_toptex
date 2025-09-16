{
    "name": "Serial Printer Web Custom",
    "version": "18.0.1.0.0",
    "category": "Website",
    "summary": "Ajustes de la vista de producto (banner/matriz)",
    "author": "Serial Printer",
    "license": "LGPL-3",
    "depends": ["website_sale"],
    "data": [
        "views/product_template.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            # Si más adelante quieres JS propio, deja esta línea
            "serial_printer_web_custom/static/src/js/product_matrix.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}