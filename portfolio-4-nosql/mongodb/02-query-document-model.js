const nexacart = db.getSiblingDB("nexacart_portfolio4");

print("QUERY 1: Electronics catalogue cards at or above NGN 40,000");
nexacart.catalogue_items.find(
  { "category.id": 1, price: { $gte: Decimal128("40000.00") } },
  { _id: 0, name: 1, price: 1, attributes: 1, review_snippets: 1 }
).forEach(printjson);

print("\nQUERY 2: Products with a storage_gb attribute (schema flexibility)");
nexacart.catalogue_items.find(
  { "attributes.storage_gb": { $exists: true } },
  { _id: 0, name: 1, "attributes.storage_gb": 1, tags: 1 }
).forEach(printjson);

print("\nQUERY 3: Average embedded review rating by category");
nexacart.catalogue_items.aggregate([
  { $unwind: "$review_snippets" },
  { $group: { _id: "$category.name", reviews: { $sum: 1 }, average_rating: { $avg: "$review_snippets.rating" } } },
  { $sort: { _id: 1 } }
]).forEach(printjson);

print("\nQUERY 4: Customer profile with embedded delivery addresses and wishlist");
nexacart.customer_profiles.find(
  { customer_id: 1 },
  { _id: 0, customer_id: 1, name: 1, addresses: 1, wishlist_product_ids: 1, preferences: 1 }
).forEach(printjson);
