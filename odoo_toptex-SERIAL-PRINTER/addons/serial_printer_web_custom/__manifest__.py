{
    "name": "Serial Printer Web Custom",
    "version": "18.0.1.0.0",
    "summary": "Matriz de variantes en la ficha de producto",
    "category": "Website/Website",
    "license": "LGPL-3",
    "depends": ["website_sale"],
    "data": [],  # ⚠️ No metas XML aquí hasta que todo funcione
    "assets": {
        "web.assets_frontend": [
            "serial_printer_web_custom/static/src/js/sp_probe.esm.js",
            "serial_printer_web_custom/static/src/js/product_matrix.esm.js",
            "serial_printer_web_custom/static/src/scss/product_matrix.scss",
        ],
    },
}