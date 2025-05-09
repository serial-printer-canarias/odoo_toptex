{
    "name": "Toptex Serial Printer Integration",
    "version": "1.0",
    "summary": "Sincroniza productos, marcas y tallas desde la API de Toptex.",
    "description": "Importación de marcas y productos desde Toptex para usarlos en ventas personalizadas.",
    "author": "Serial Printer",
    "website": "https://serialprintercanarias.com",
    "category": "Sales",
    "depends": ["base", "product", "sale", "purchase"],
    "data": [
        "views/toptex_brand_import_button.xml"
    ],
    "installable": True,
    "application": True,
    "auto_install": False
}