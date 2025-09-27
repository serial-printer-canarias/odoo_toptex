# -*- coding: utf-8 -*-
{
    "name": "Serial Printer - Custom Wizard",
    "version": "18.0.1.0.1",
    "summary": "Personalización de producto con vista previa de logo.",
    "category": "Website/Website",
    "license": "LGPL-3",
    "depends": ["website_sale"],
    "data": [
        "views/customizer_page.xml",
        "views/product_personalize_button.xml",
        # NO tocamos QWeb para el carrito
    ],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_custom_wizard/static/src/css/personalizar_preview.css",
            "serial_printer_custom_wizard/static/src/js/spw_cart_preview.inject.js",
        ],
    },
    "installable": True,
    "application": False,
}