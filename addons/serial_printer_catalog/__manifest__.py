{
    'name': 'Catálogo TopTex',
    'version': '1.0.0',
    'category': 'Sales',
    'summary': 'Importación de productos TopTex',
    'description': 'Crea productos desde la API de TopTex en el modelo estándar de Sales.',
    'author': 'Serial Printer',
    'depends': ['base', 'product'],
    'data': [
        'data/cron_product.xml',  # Esto sí lo dejamos si quieres mantener la acción programada
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}