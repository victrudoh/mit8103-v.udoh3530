const nexacart = db.getSiblingDB("nexacart_portfolio4");

function pass(name, condition) {
  if (!condition) {
    throw new Error("FAIL: " + name);
  }
  print("PASS: " + name);
}

pass("seven catalogue documents seeded", nexacart.catalogue_items.countDocuments() === 7);
pass("two embedded customer profiles seeded", nexacart.customer_profiles.countDocuments() === 2);
pass("source product IDs are unique", nexacart.catalogue_items.distinct("source.postgres_product_id").length === 7);
const catalogueIds = nexacart.catalogue_items.distinct("source.postgres_product_id");
const wishlistIds = nexacart.customer_profiles.aggregate([
  { $unwind: "$wishlist_product_ids" },
  { $group: { _id: "$wishlist_product_ids" } }
]).toArray().map(row => row._id);
pass("every wishlist product ID resolves to a catalogue document", wishlistIds.every(id => catalogueIds.includes(id)));
pass("smartphone carries a product-specific storage attribute", nexacart.catalogue_items.countDocuments({ "attributes.storage_gb": 128 }) === 1);
pass("Amara profile embeds two addresses", nexacart.customer_profiles.countDocuments({ customer_id: 1, "addresses.1": { $exists: true } }) === 1);
pass("catalogue category-price index exists", nexacart.catalogue_items.getIndexes().some(index => index.name === "category_price"));

let rejected = false;
try {
  nexacart.catalogue_items.insertOne({ sku: "P4-INVALID" });
} catch (error) {
  rejected = error.code === 121;
}
pass("schema validation rejects an incomplete catalogue document", rejected);
pass("invalid document was not stored", nexacart.catalogue_items.countDocuments({ sku: "P4-INVALID" }) === 0);

print("VALIDATION COMPLETE");
