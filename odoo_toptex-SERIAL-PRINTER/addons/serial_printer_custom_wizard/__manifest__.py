{
    "name": "Serial Printer - Custom Wizard",
    "version": "18.0.1.0.0",
    "summary": "Botón Personalizar en ficha de producto + página /personalizar/<id>",
    "category": "Website/Website",
    "depends": ["website_sale"],
    "data": [
        "views/website_customize_button.xml",
        "views/assets.xml",  # solo para cargar el JS de prueba (opcional)
        # si tienes la página /personalizar/, aquí iría su XML (NO otro inherit del product):
        # "views/personalizacion_wizard_website_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}