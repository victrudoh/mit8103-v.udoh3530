const nexacart = db.getSiblingDB("nexacart_portfolio4");

// The Query 1 filter from 02-query-document-model.js: Electronics at or above NGN 40,000.
const filter = { "category.id": 1, price: { $gte: Decimal128("40000.00") } };

// Collect the stage names of the winning plan, innermost stage last.
// MongoDB 8 may wrap the classic plan inside `queryPlan`.
function stages(plan) {
  const root = plan.queryPlan || plan;
  const names = [];
  let node = root;
  while (node) {
    names.push(node.stage + (node.indexName ? " (" + node.indexName + ")" : ""));
    node = node.inputStage;
  }
  return names;
}

function summarise(label, cursor) {
  const explain = cursor.explain("executionStats");
  const stats = explain.executionStats;
  print(label);
  print("  plan stages (outer -> inner): " + stages(explain.queryPlanner.winningPlan).join(" -> "));
  print("  nReturned=" + stats.nReturned + " keysExamined=" + stats.totalKeysExamined +
        " docsExamined=" + stats.totalDocsExamined);
  return stats;
}

print("EXPLAIN 1: category + price query using the default planner");
const indexed = summarise("  default planner choice", nexacart.catalogue_items.find(filter));

print("\nEXPLAIN 2: same query forced to a collection scan with hint({ $natural: 1 })");
const scanned = summarise("  forced collection scan", nexacart.catalogue_items.find(filter).hint({ $natural: 1 }));

print("\nEXPLAIN 3: tag lookup using the multikey tags index");
const tagged = summarise("  tags: 'smartphone'", nexacart.catalogue_items.find({ tags: "smartphone" }));

function pass(name, condition) {
  if (!condition) {
    throw new Error("FAIL: " + name);
  }
  print("PASS: " + name);
}

print("\nCHECKS");
pass("default plan uses the category_price index",
  JSON.stringify(nexacart.catalogue_items.find(filter).explain().queryPlanner.winningPlan).includes('"indexName":"category_price"'));
pass("indexed query examines fewer documents than a collection scan", indexed.totalDocsExamined < scanned.totalDocsExamined);
pass("both plans return the same documents", indexed.nReturned === scanned.nReturned);
pass("tag query uses the tags index",
  JSON.stringify(nexacart.catalogue_items.find({ tags: "smartphone" }).explain().queryPlanner.winningPlan).includes('"indexName":"tags"'));
print("EXPLAIN COMPLETE");
