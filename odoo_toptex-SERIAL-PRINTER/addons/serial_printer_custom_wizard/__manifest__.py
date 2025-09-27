# -*- coding: utf-8 -*-
{
    "name": "Serial Printer - Custom Wizard",
    "version": "18.0.1.3.0",   # súbela en cada commit
    "summary": "Personalización con preview y múltiples imágenes por línea.",
    "category": "Website/Website",
    "license": "LGPL-3",
    "depends": ["website_sale"],

    "data": [
        "views/customizer_page.xml",
        "views/product_personalize_button.xml",
    ],

    "assets": {
        "web.assets_frontend": [
            # ===== CSS (OJO: carpeta 'CSS' en mayúsculas) =====
            "serial_printer_custom_wizard/static/src/CSS/customizer.css",
            "serial_printer_custom_wizard/static/src/CSS/personalizar_preview.css",
            "serial_printer_custom_wizard/static/src/CSS/spw.css",
            "serial_printer_custom_wizard/static/src/CSS/spw_colors.css",

            # ===== JS utilidades / base =====
            "serial_printer_custom_wizard/static/src/js/spw_public.js",
            "serial_printer_custom_wizard/static/src/js/spw.js",
            "serial_printer_custom_wizard/static/src/js/spw_options.js",
            "serial_printer_custom_wizard/static/src/js/ns300_colors.js",

            # ===== Botón / colocación =====
            "serial_printer_custom_wizard/static/src/js/spw_button.js",
            "serial_printer_custom_wizard/static/src/js/personalize_btn.js",
            "serial_printer_custom_wizard/static/src/js/add_customize_button.js",
            "serial_printer_custom_wizard/static/src/js/move_personalize_btn.js",
            "serial_printer_custom_wizard/static/src/js/spw_force_customize_button.js",

            # ===== Customizer / previews =====
            "serial_printer_custom_wizard/static/src/js/spw_customizer.js",
            "serial_printer_custom_wizard/static/src/js/customizer.js",
            "serial_printer_custom_wizard/static/src/js/customizer_enhancements.js",
            "serial_printer_custom_wizard/static/src/js/customizer_preview.js",
            "serial_printer_custom_wizard/static/src/js/spw_logo_preview.js",
            "serial_printer_custom_wizard/static/src/js/personalizacion.js",

            # ===== Carrito =====
            "serial_printer_custom_wizard/static/src/js/spw_cart.js",
            "serial_printer_custom_wizard/static/src/js/spw_cart_preview.inject.js",
        ],
    },

    "installable": True,
    "application": False,
    "auto_install": False,
}