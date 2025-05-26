{
    'name': 'Catálogo Serial Printer',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Catálogo con integración a API TopTex',
    'description': 'Sincroniza productos, marcas, variantes, precios e imágenes desde la API de TopTex.',
    'author': 'Serial Printer',
    'depends': ['base', 'sale', 'product'],
    'data': [
        # Menú raíz
        'views/menu_root.xml',

        # Productos
        'views/menu_product.xml',
        'views/product_views.xml',
        'data/cron_product.xml',

        # Marcas
        'views/menu_brand.xml',
        'views/brand_views.xml',
        'data/cron_brand.xml',

        # Atributos
        'views/menu_attribute.xml',
        'views/attribute_views.xml',
        'data/cron_attribute.xml',

        # Variantes
        'views/menu_variant.xml',
        'views/variant_views.xml',
        'data/cron_variant.xml',

        # Imágenes
        'views/menu_image.xml',
        'views/image_views.xml',
        'data/cron_image.xml',

        # Precios
        'views/menu_prices.xml',
        'views/prices_views.xml',
        'data/cron_prices.xml',

        # Stock
        'data/cron_stock.xml',

        # Token (sin menú visible)
        'views/token_views.xml',
        'data/token_default.xml',
        'data/cron_token.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}