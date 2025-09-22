# __manifest__.py
{
    "name": "Serial Printer - Web Custom (Matrix)",
    "version": "18.0.1.0.0",
    "license": "LGPL-3",
    "category": "Website",
    "summary": "Grid de cantidades por color/talla en la ficha de producto",
    "depends": ["website_sale"],
    "data": [],  # sin XML ni xpaths
    "assets": {
        # Cargar en TODO el frontend (el JS se auto-limita a la ficha de producto)
        "web.assets_frontend": [
            "serial_printer_web_custom/static/src/js/product_matrix.js",
            "serial_printer_web_custom/static/src/scss/product_matrix.scss",
        ],
    },
    "installable": True,
    "application": False,
}