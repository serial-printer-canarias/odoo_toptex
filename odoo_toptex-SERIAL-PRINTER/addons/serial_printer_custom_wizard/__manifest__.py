# -*- coding: utf-8 -*-
{
    "name": "Serial Printer - Custom Wizard",
    "version": "18.0.1.0.1",
    "summary": "Botón “Personalizar” en la ficha de producto, página de personalización y wizard.",
    "category": "Website/Website",
    "license": "LGPL-3",
    "author": "Serial Printer Canarias",
    "website": "https://serial-printer-canarias-odoo-toptex.odoo.com",
    "depends": ["base", "web", "website", "website_sale"],
    "data": [
        # Seguridad (si ya existe tu CSV, déjalo; si no existe, elimina esta línea)
        "security/ir.model.access.csv",

        # Botón y plantillas web
        "views/website_customize_button.xml",
        "views/website_customize_template.xml",

        # Vistas del wizard / formulario
        "views/personalizacion_form.xml",
        "views/personalizacion_wizard_views.xml",
        "views/personalizacion_wizard_website_-views.xml",

        # Declaración de assets vía XML (debe ser XML bien formado)
        "views/assets.xml",
    ],
    # Carga directa del JS desde el manifest (refuerzo; no choca con assets.xml)
    "assets": {
        "web.assets_frontend": [
            "serial_printer_custom_wizard/static/src/js/add_customize_button.js",
        ],
    },
    "installable": True,
    "application": False,
}