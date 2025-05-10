
{
    "name": "Catálogo Serial Printer",
    "version": "1.0",
    "summary": "Gestión de marcas externas para personalización",
    "description": "Importa marcas desde proveedor externo y organízalas en tu catálogo.",
    "author": "Serial Printer",
    "website": "https://serialprintercanarias.com",
    "category": "Sales",
    "depends": ["base", "product", "sale", "purchase"],
    "data": [
        "views/toptex_brand_views.xml",
        "views/toptex_brand_import_button.xml",
        "views/toptex_menus.xml"
    ],
    "installable": True,
    "application": True,
    "auto_install": False
}
