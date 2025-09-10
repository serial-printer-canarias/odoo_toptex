{
    "name": "Serial Printer - Custom Wizard",
    "version": "0.4.0",
    "category": "Website/Website",
    "summary": "Botón “Personalizar” + página simple",
    "depends": ["website_sale"],
    "data": [
        # seguridad si la tienes
        "security/ir.model.access.csv",
        # página de destino /spw/personalizar/<id>
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