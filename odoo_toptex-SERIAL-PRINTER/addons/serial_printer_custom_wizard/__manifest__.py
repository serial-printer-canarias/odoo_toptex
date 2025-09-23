# -*- coding: utf-8 -*-
{
    "name": "Serial Printer - Custom Wizard",
    "version": "18.0.1.0.0",
    "summary": "Personalización de producto con vista previa de logo.",
    "category": "Website/Website",
    "license": "LGPL-3",
    "depends": ["website_sale"],
    "data": [
        "views/customizer_page.xml",
        "views/product_personalize_button.xml",
        # ⚠️ QUITA el XML que daba error de XPath:
        # "views/spw_cart_preview_qweb.xml",
        # ⚠️ Y no cargues ya ningún “*_inject.xml”
    ],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_custom_wizard/static/src/js/spw_button.js",
            "serial_printer_custom_wizard/static/src/js/spw_logo_preview.js",
            "serial_printer_custom_wizard/static/src/js/customizer.js",
            "serial_printer_custom_wizard/static/src/js/ns300_colors.js",
            "serial_printer_custom_wizard/static/src/js/spw_options.js",
            "serial_printer_custom_wizard/static/src/js/spw_cart.js",
            "serial_printer_custom_wizard/static/src/js/spw.js",
            "serial_printer_custom_wizard/static/src/js/spw_cart_preview.inject.js",  # ⬅️ NUEVO
            "serial_printer_custom_wizard/static/src/css/spw.css",
        ],
    },
    "installable": True,
    "application": False,
}