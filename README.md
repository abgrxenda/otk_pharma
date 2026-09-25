# 💊 Pharma B2B Suite for Odoo 18.0

Onboard partner pharmacies, control restricted items, sell kits and keep drug data on every
product, all inside Odoo. Install one module and get the whole suite.

![Odoo Version](https://img.shields.io/badge/Odoo-18.0-blue)
![License](https://img.shields.io/badge/license-OPL--1-blue)
![Python](https://img.shields.io/badge/Python-3-yellow?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?logo=postgresql&logoColor=white)
![Status](https://img.shields.io/badge/status-in%20development-yellow)

## 📖 Overview

Pharma B2B Suite is a set of four Odoo 18 modules for a wholesale pharmacy that supplies smaller
partner pharmacies. It covers the whole relationship: how a pharmacy becomes a customer, what it
is allowed to order, how sensitive items are released, and how kits and drug data are kept on your
products. Everything runs inside standard Odoo, with a website portal for your pharmacies and the
normal backend for your team.

The suite is under active development. Each module's version is in its `__manifest__.py`.

### 🎯 What it solves

- **Signup paperwork**: the application, licence upload and contract signature happen online
  instead of through email attachments and scanned PDFs.
- **Control over sensitive items**: controlled and prescription products cannot be sold without an
  approval or the right documents, and every release leaves a record.
- **Consistent pricing**: each pharmacy gets its own pricelist, and kits are priced from it.
- **Product data you are expected to keep**: DIN, schedule, MLP, LCAP and more, right on the
  product form.

### 👥 Who it is for

Wholesale pharmacies, distributors and kit or compound suppliers that sell to a known group of
approved partner pharmacies, rather than to the general public.

### 🧩 How it is built

- **Four focused modules and one bundle**: install only what you need, or everything at once.
- **Core Odoo only**: no third-party modules are required, so there is nothing extra to buy,
  install or keep in step with your Odoo version.
- **Portal and backend**: pharmacies work in their website account, your team works in the Odoo
  backend, and status changes are logged in the chatter.
- **Tested on Odoo 18**: installed on a clean database and exercised end to end, including
  registration, contract signing, approvals and kit pricing.
- **Regional defaults**: DIN, provincial licence numbers and province and postal code fields follow
  Canadian conventions. The fields are plain text, so they work elsewhere too.

This software helps you organise your process. You remain responsible for meeting the pharmacy
and controlled-substance rules that apply where you operate.

## 🗂️ Modules

| Module | Technical name | What it does |
|---|---|---|
| Pharma B2B Suite | `otk_pharma` | Installs the four modules below in one step. Contains no code. |
| Pharma B2B Onboarding | `otk_pharma_onboarding` | Public registration, on-screen contract signature, approval, customer and portal login creation. |
| Pharma Item Approval | `otk_pharma_item_approval` | Holds orders with controlled or prescription items until approved, with one-time approval codes. |
| Pharma BOM & Kit Management | `otk_pharma_bomkit` | Kits and compounds built from components, priced from each pharmacy's pricelist. |
| Pharma Product Fields | `otk_pharma_product_fields` | DIN, generic and brand name, manufacturer code, schedule, MLP, LCAP and tier on products. |

Each module can also be installed on its own. The modules it needs are installed with it.

## 🧭 The customer journey

1. **Apply**: the pharmacy fills in the public form at `/pharmacy/register`.
2. **Sign**: it signs the contract on screen and a PDF is generated.
3. **Activate**: you review the application, choose a pricelist (discount tier) and a delivery fee,
   and approve. The customer record and a portal login are created and a welcome email is sent.
   A rejection needs a reason, which is included in the email.
4. **Order**: the pharmacy orders on your website. At checkout it can confirm on credit, within its
   credit limit.
5. **Approve**: an order that contains a product flagged "requires approval" or "requires
   prescription" is held (Pending Approval or Pending Prescription). Pharmacies upload
   prescriptions from their portal.
6. **Release**: when you approve, a six-digit one-time code (valid 24 hours) is emailed to the
   pharmacy, which enters it in its portal to confirm the order. Only a hash of the code is stored,
   and unused codes expire automatically every hour.

## ✅ Requirements

- Odoo 18.0
- These Odoo apps are installed automatically: Sales, Inventory, Invoicing, Website, eCommerce,
  Portal, Discuss
- An outgoing email server (welcome, rejection and approval-code emails)

No third-party modules are required.

## 🚀 Installation

1. Put all five module folders in your Odoo addons path.
2. Restart Odoo and update the Apps list (Apps, then Update Apps List).
3. Install **Pharma B2B Suite**.

Uninstalling the suite does not remove the four modules it installed.

## ⚙️ Setup after installing

- **Email**: configure an outgoing mail server and set your company email.
- **Pricelists**: create the pricelists you want to use as discount tiers. You choose one for each
  pharmacy when you approve its application.
- **Delivery fee**: set per pharmacy when approving an application.
- **Credit limit**: set Odoo's standard credit limit on the customer if you want checkout to enforce it.
- **Products**: tick "Requires approval" and/or "Requires prescription" on controlled products, and
  fill in the Pharmacy Fields tab.

## 📍 Where things are

| Area | Location |
|---|---|
| Applications | Pharmacy B2B, then Onboarding, then Applications (`/odoo/pharmacy-onboarding`) |
| Held orders | Pharma Approvals, then All Orders (`/odoo/pharma-approvals`) |
| Kits | Pharma BOM & Kits, then BOM / Kit Definitions (`/odoo/pharma-bom-kits`) |
| Public registration | `/pharmacy/register` |
| Pharmacy portal | `/my/pending-approvals` and `/my/prescription-uploads` |

## 🧱 Repository layout

Each module is a folder at the top level of the branch, next to this file:

```
otk_pharma/
otk_pharma_onboarding/
otk_pharma_item_approval/
otk_pharma_bomkit/
otk_pharma_product_fields/
README.md
```

## 📝 License

All modules in this repository are licensed under OPL-1 (Odoo Proprietary License v1.0). **Pharma B2B Suite**
(`otk_pharma`), which installs the four modules, is sold on the Odoo Apps store for USD 150 (one-time
purchase). See the `license` key in each module's `__manifest__.py`.

## 👤 Author and support

**Ömer Kadir | Ömer Teknoloji**
- Website: [omertek.com](https://omertek.com)
- Support: support@omertek.com
