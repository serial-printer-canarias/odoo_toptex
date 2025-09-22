# __manifest__.py  (Odoo 18)
{
    "name": "Serial Printer - Web Custom (Matrix)",
    "version": "18.0.1.0.0",
    "license": "LGPL-3",
    "category": "Website",
    "summary": "Grid de cantidades por color/talla en la ficha de producto",
    "depends": ["website_sale"],
    "data": [],  # ¡SIN XML para evitar el error de xpath!
    "assets": {
        # Bundle específico de eCommerce
        "website.assets_wsale": [
            "serial_printer_web_custom/static/src/js/product_matrix.js",
            "serial_printer_web_custom/static/src/scss/product_matrix.scss",
        ],
    },
    "installable": True,
    "application": False,
}