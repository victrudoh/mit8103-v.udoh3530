const nexacart = db.getSiblingDB("nexacart_portfolio4");

nexacart.catalogue_items.drop();
nexacart.customer_profiles.drop();

nexacart.createCollection("catalogue_items", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["source", "sku", "name", "category", "price", "is_active", "attributes", "tags", "review_snippets", "created_at"],
      properties: {
        source: { bsonType: "object", required: ["postgres_product_id"], properties: { postgres_product_id: { bsonType: ["int", "long"] } } },
        sku: { bsonType: "string" },
        name: { bsonType: "string" },
        category: { bsonType: "object", required: ["id", "name"], properties: { id: { bsonType: ["int", "long"] }, name: { bsonType: "string" } } },
        price: { bsonType: "decimal" },
        is_active: { bsonType: "bool" },
        attributes: { bsonType: "object" },
        tags: { bsonType: "array" },
        review_snippets: { bsonType: "array" },
        created_at: { bsonType: "date" }
      }
    }
  },
  validationLevel: "strict",
  validationAction: "error"
});

nexacart.createCollection("customer_profiles", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["customer_id", "name", "contact", "addresses", "wishlist_product_ids"],
      properties: {
        customer_id: { bsonType: ["int", "long"] },
        name: { bsonType: "object" },
        contact: { bsonType: "object" },
        addresses: { bsonType: "array" },
        wishlist_product_ids: { bsonType: "array" }
      }
    }
  },
  validationLevel: "strict",
  validationAction: "error"
});

nexacart.catalogue_items.insertMany([
  {
    source: { postgres_product_id: 1 }, sku: "NCX-EL-001", name: "NexaOne Smartphone",
    category: { id: 1, name: "Electronics" }, price: Decimal128("380000.00"), is_active: true,
    attributes: { storage_gb: 128, ram_gb: 8, operating_system: "Android", colour_options: ["black", "blue"] },
    tags: ["smartphone", "android", "mobile"],
    review_snippets: [{ customer_id: 1, rating: 4, excerpt: "Fast and reliable battery life.", created_at: ISODate("2026-09-18T09:00:00Z") }],
    created_at: ISODate("2026-09-08T09:00:00Z")
  },
  {
    source: { postgres_product_id: 2 }, sku: "NCX-EL-002", name: "ClearSound Wireless Earbuds",
    category: { id: 1, name: "Electronics" }, price: Decimal128("42000.00"), is_active: true,
    attributes: { connectivity: "Bluetooth", charging_case: true, battery_hours: 24 },
    tags: ["audio", "wireless", "bluetooth"],
    review_snippets: [{ customer_id: 1, rating: 5, excerpt: "Clear audio and easy pairing.", created_at: ISODate("2026-09-18T09:10:00Z") }],
    created_at: ISODate("2026-09-08T09:10:00Z")
  },
  {
    source: { postgres_product_id: 3 }, sku: "NCX-EL-003", name: "LiteBook 14 Laptop",
    category: { id: 1, name: "Electronics" }, price: Decimal128("620000.00"), is_active: true,
    attributes: { screen_inches: 14, ram_gb: 16, storage_gb: 512, weight_kg: 1.3 },
    tags: ["laptop", "study", "office"], review_snippets: [],
    created_at: ISODate("2026-09-08T09:20:00Z")
  },
  {
    source: { postgres_product_id: 5 }, sku: "NCX-FA-005", name: "Classic Cotton T-Shirt",
    category: { id: 2, name: "Fashion" }, price: Decimal128("8500.00"), is_active: true,
    attributes: { fabric: "cotton", available_sizes: ["S", "M", "L", "XL"], fit: "regular" },
    tags: ["fashion", "cotton", "casual"], review_snippets: [],
    created_at: ISODate("2026-09-08T10:00:00Z")
  },
  {
    source: { postgres_product_id: 8 }, sku: "NCX-HK-008", name: "KitchenPro Blender",
    category: { id: 3, name: "Home and Kitchen" }, price: Decimal128("39000.00"), is_active: true,
    attributes: { speeds: 5, capacity_litres: 1.5, dishwasher_safe_parts: true },
    tags: ["kitchen", "blender", "appliance"],
    review_snippets: [{ customer_id: 4, rating: 4, excerpt: "Powerful enough for daily use.", created_at: ISODate("2026-09-19T12:15:00Z") }],
    created_at: ISODate("2026-09-08T11:00:00Z")
  },
  {
    source: { postgres_product_id: 13 }, sku: "NCX-GR-013", name: "Premium Rice 10kg",
    category: { id: 5, name: "Groceries" }, price: Decimal128("32000.00"), is_active: true,
    attributes: { weight_kg: 10, rice_type: "parboiled", origin: "Nigeria" },
    tags: ["groceries", "rice", "pantry"],
    review_snippets: [{ customer_id: 5, rating: 5, excerpt: "Good quality and convenient package size.", created_at: ISODate("2026-09-20T08:45:00Z") }],
    created_at: ISODate("2026-09-08T13:00:00Z")
  },
  {
    source: { postgres_product_id: 16 }, sku: "NCX-BK-016", name: "Database Systems Textbook",
    category: { id: 6, name: "Books and Stationery" }, price: Decimal128("28500.00"), is_active: true,
    attributes: { subject: "database systems", format: "paperback", audience: "undergraduate" },
    tags: ["books", "database", "education"],
    review_snippets: [{ customer_id: 6, rating: 4, excerpt: "Useful reference for database design.", created_at: ISODate("2026-09-20T14:20:00Z") }],
    created_at: ISODate("2026-09-08T14:00:00Z")
  }
]);

nexacart.customer_profiles.insertMany([
  {
    customer_id: 1, name: { first: "Amara", last: "Okafor" },
    contact: { email: "amara.okafor@nexacart.example", phone: "+2348015550101" },
    addresses: [
      { label: "home", street: "12 Admiralty Way", city: "Lekki", state: "Lagos", country: "Nigeria" },
      { label: "work", street: "8 Allen Avenue", city: "Ikeja", state: "Lagos", country: "Nigeria" }
    ],
    wishlist_product_ids: [3, 8],
    preferences: { newsletter_opt_in: true, preferred_categories: ["Electronics", "Books and Stationery"] }
  },
  {
    customer_id: 3, name: { first: "Zainab", last: "Bello" },
    contact: { email: "zainab.bello@nexacart.example", phone: "+2348015550103" },
    addresses: [
      { label: "home", street: "19 Tafawa Balewa Road", city: "Kano", state: "Kano", country: "Nigeria" },
      { label: "alternate", street: "7 Wuse Market Road", city: "Wuse", state: "FCT", country: "Nigeria" }
    ],
    wishlist_product_ids: [1, 16],
    preferences: { newsletter_opt_in: false, preferred_categories: ["Electronics"] }
  }
]);

nexacart.catalogue_items.createIndex({ "source.postgres_product_id": 1 }, { unique: true, name: "source_product_id_unique" });
nexacart.catalogue_items.createIndex({ "category.id": 1, price: 1 }, { name: "category_price" });
nexacart.catalogue_items.createIndex({ tags: 1 }, { name: "tags" });
nexacart.customer_profiles.createIndex({ customer_id: 1 }, { unique: true, name: "customer_id_unique" });

print("SEEDED DOCUMENT MODEL");
print("catalogue_items=" + nexacart.catalogue_items.countDocuments());
print("customer_profiles=" + nexacart.customer_profiles.countDocuments());
print("indexes=" + nexacart.catalogue_items.getIndexes().map(index => index.name).join(", "));
