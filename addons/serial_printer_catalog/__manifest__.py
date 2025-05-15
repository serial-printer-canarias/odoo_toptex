
{
    "name": "Catálogo de Marcas",
    "version": "1.0",
    "summary": "Gestión de marcas externas",
    "sequence": 10,
    "description": "Base para integrar productos y marcas con API externa.",
    "category": "Sales",
    "author": "Tu Empresa",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/toptex_brand_views.xml",
        "views/menu.xml"
    ],
    "installable": True,
    "application": True,
    "auto_install": False
}
