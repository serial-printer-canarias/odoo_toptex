{
    'name': 'Serial Printer Catalog',
    'version': '1.0',
    'summary': 'Catálogo sincronizado con API externa',
    'description': 'Importa marcas, productos, variantes, atributos y stock desde la API de TopTex',
    'author': 'Serial Printer',
    'category': 'Sales',
    'depends': ['base', 'product'],
    'data': [
        # Menú raíz
        'views/menu_root.xml',

        # Marcas
        'views/brand_views.xml',
        'views/menu_brands.xml',
        'data/cron_brand.xml',

        # Atributos
        'views/attribute_views.xml',
        'views/menu_attribute.xml',
        'data/cron_attribute.xml',

        # Variantes
        'views/variant_views.xml',
        'views/menu_variant.xml',
        'data/cron_variant.xml',

        # Productos
        'views/product_views.xml',
        'views/menu_product.xml',
        'data/cron_product.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}