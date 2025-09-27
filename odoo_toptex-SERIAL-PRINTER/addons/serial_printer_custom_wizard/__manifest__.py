# -*- coding: utf-8 -*-
{
    "name": "Serial Printer - Custom Wizard",
    "version": "18.0.1.0.8",  # sube 1 dígito al actualizar
    "summary": "Personalización de producto con vista previa y adjuntos al carrito.",
    "author": "Serial Printer Canarias",
    "website": "https://serial-printer-canarias-odoo-toptex.odoo.com",
    "category": "Website/Website",
    "license": "LGPL-3",
    "depends": ["website_sale"],

    # SOLO ficheros XML que realmente existen en tu módulo
    "data": [
        "views/customizer_page.xml",
        "views/product_personalize_button.xml",
    ],

    # SOLO si existe el JS EXACTAMENTE en esa ruta
    "assets": {
        "web.assets_frontend": [
            "serial_printer_custom_wizard/static/src/js/spw_button.js",
        ],
    },

    "installable": True,
    "application": False,
    "auto_install": False,
}