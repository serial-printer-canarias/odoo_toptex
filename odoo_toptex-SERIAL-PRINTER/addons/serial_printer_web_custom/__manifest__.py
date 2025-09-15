{
    "name": "Serial Printer Web Custom",
    "version": "18.0.1.0.3",  # ⬅️ subido para forzar upgrade
    "category": "Website/eCommerce",
    "summary": "Matriz color × talla con stock, precio e inputs; botón de añadir por color",
    "author": "Serial Printer",
    "website": "https://serial-printer.com",
    "license": "LGPL-3",
    "depends": ["website_sale"],
    "data": ["views/product_template.xml"],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_web_custom/static/src/js/product_matrix.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}