{
    'name': 'Catálogo',
    'version': '1.0.0',
    'category': 'Sales',
    'summary': 'Catálogo de productos con integración API',
    'description': 'Sincroniza productos, marcas, variantes e imágenes desde la API de TopTex.',
    'depends': ['base', 'sale', 'product'],
    'data': [
        # Menú raíz
        'views/menu_root.xml',

        # Marcas
        'views/menu_brand.xml',
        'views/brand_views.xml',
        'data/cron_brand.xml',

        # Productos
        'views/menu_product.xml',
        'views/product_views.xml',
        'data/cron_product.xml',

        # Atributos y variantes
        'views/menu_attribute.xml',
        'views/attribute_views.xml',
        'data/cron_attribute.xml',

        'views/menu_variant.xml',
        'views/variant_views.xml',
        'data/cron_variant.xml',

        # Imágenes
        'data/cron_image.xml',

        # Precios
        'views/menu_prices.xml',
        'views/prices_views.xml',
        'data/cron_prices.xml',

        # Stock
        'data/cron_stock.xml',

        # Token
        'views/menu_token.xml',
        'views/token_views.xml',
        'data/cron_token.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}