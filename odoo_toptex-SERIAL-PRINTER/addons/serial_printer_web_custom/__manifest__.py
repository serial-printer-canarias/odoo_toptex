# __manifest__.py
{
    "name": "Serial Printer – Web Custom",
    "version": "18.0.0.0",
    "summary": "Grid por color/talla en la ficha de producto",
    "depends": ["website_sale"],
    "assets": {
        "web.assets_frontend": [
            # 1) PROBE: comprueba que el bundle se carga
            "serial_printer_web_custom/static/src/js/sp_probe.js",
            # 2) Grid real
            "serial_printer_web_custom/static/src/js/product_matrix.js",
            "serial_printer_web_custom/static/src/scss/product_matrix.scss",
        ],
    },
    # Hook opcional y seguro (no mueve nada, solo pone un data-atributo).
    "data": [
        "serial_printer_web_custom/views/product_template.xml",
    ],
    "license": "LGPL-3",
}