{
    'name': 'Catálogo TopTex',
    'version': '1.0.0',
    'category': 'Sales',
    'summary': 'Importación de productos TopTex (NS300)',
    'description': 'Crea productos desde TopTex directamente en Sales',
    'author': 'Serial Printer',
    'depends': ['base', 'product'],
    'data': [
        'data/cron_product.xml',  
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}