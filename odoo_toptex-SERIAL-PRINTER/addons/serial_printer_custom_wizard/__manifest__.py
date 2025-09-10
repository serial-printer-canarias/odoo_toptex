{
    "name": "Serial Printer - Custom Wizard",
    "version": "0.4.2",
    "category": "Website/Website",
    "summary": "Botón “Personalizar” (JS) + página de prueba",
    "depends": ["website_sale"],
    "data": [
        "views/personalizacion_wizard_website_views.xml"
    ],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_custom_wizard/static/src/js/add_customize_button.js",
        ]
    },
    "installable": True,
    "application": False,
}