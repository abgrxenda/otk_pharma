{
    'name': 'Pharma BOM & Kit Management',
    'version': '18.0.2.6.0',
    'category': 'Pharmacy',
    'summary': 'Bill of Materials and Kit assembly for pharmacy products with pricelist tier management',
    'description': """
Pharma BOM & Kit Management
===========================

* Define Bill of Materials for pharmacy kit/compound products
* Kits explode on order confirm (configurable: show components or keep as single line)
* Enhanced pricelist tier views with quantity breaks
* Per-pharmacy pricing via native Odoo pricelists with improved UI
    """,
    'author': 'Omer Kadir',
    'depends': [
        'base',
        'mail',
        'product',
        'sale',
        'sale_management',
        'stock',
        'uom',
        'otk_pharma_onboarding',
        'otk_pharma_item_approval',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/backend_views.xml',
        'views/portal_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
