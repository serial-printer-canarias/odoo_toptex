{
    'name': 'Importación producto TopTex NS300',
    'version': '1.0.0',
    'category': 'Sales',
    'summary': 'Crea el producto NS300 desde TopTex',
    'description': 'Llama a la API de TopTex y crea el producto NS300 directamente en Sales',
    'author': 'Serial Printer',
    'depends': ['base', 'product', 'sale'],
    'data': [
        'data/cron_product.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}