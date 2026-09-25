{
    'name': 'Pharma Product Fields',
    'version': '18.0.1.0.0',
    'category': 'Pharmacy',
    'summary': 'Custom fields for pharmacy products',
    'description': """
        Adds pharmacy-specific fields to product templates:
        - DIN (Drug Identification Number)
        - Generic Name, Brand Name
        - Manufacturer Code
        - Schedule Category
        - MLP (Max Listed Price), LCAP (Lowest Alt Price)
        - Tier
        
        Note: Require Prescription and Require Approval fields
        are already provided by otk_pharma_item_approval module.
        Pack Size and On Hand Quantity are standard Odoo fields.
    """,
    'author': 'Omer Kadir',
    'depends': [
        'base',
        'product',
        'otk_pharma_onboarding',
        'otk_pharma_item_approval',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
    ],
    'images': [
        'static/description/pharma-product-tabs.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
