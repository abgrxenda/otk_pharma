{
    'name': 'Pharma B2B Suite',
    'version': '18.0.1.0.0',
    'category': 'Pharmacy',
    'summary': 'One-click install of the complete pharmacy B2B suite',
    'description': """
        Installs the complete Pharma B2B suite in one step:
        - Pharma B2B Onboarding (registration, digital contract, activation)
        - Pharma Item Approval (controlled item approval gate)
        - Pharma BOM & Kit Management (kits and pricing tiers)
        - Pharma Product Fields (DIN, brand, schedule and more)

        This module contains no code of its own. Uninstalling it does not
        remove the four modules above.
    """,
    'author': 'Omer Kadir',
    'depends': [
        'otk_pharma_onboarding',
        'otk_pharma_item_approval',
        'otk_pharma_bomkit',
        'otk_pharma_product_fields',
    ],
    'data': [],
    'images': [
        'static/description/pharmacy-register.png',
        'static/description/pharmacy-b2b.png',
        'static/description/pharma-approval.png',
        'static/description/pharma-bom.png',
        'static/description/pharma-product-tabs.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
