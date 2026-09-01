/**
 * pnl-orders.cjs — read-only order export for the break-even calculator.
 *
 *   B64=$(base64 -w0 pnl-orders.cjs)
 *   railway ssh --service NOS_prod -i ~/.ssh/railway-nos \
 *     "echo $B64 | base64 -d > /tmp/p.cjs && cd /app && SINCE=2026-06-01 \
 *      NODE_PATH=/app/node_modules node /tmp/p.cjs"
 *
 * Superset of cogs-orders.cjs: adds `email` (to strip test orders) and
 * `refunded` (to net revenue down). SELECT only.
 *
 * Gotchas encoded here so they are not rediscovered:
 *   - order_summary has many versions per order; take the latest by version.
 *   - payment_collection has NO order_id — join through order_payment_collection.
 *   - order_line_item has no quantity; it lives on order_item.
 *   - "order" is a reserved word and must be quoted.
 */
const { Client } = require("pg");
const ISBN = /^\d{10,13}$/;

(async () => {
  const c = new Client({ connectionString: process.env.DATABASE_URL, ssl: { rejectUnauthorized: false } });
  await c.connect();
  const since = process.env.SINCE || "2026-06-01";

  const { rows } = await c.query(`
    WITH ls AS (
      SELECT DISTINCT ON (order_id) order_id, totals FROM order_summary
      WHERE deleted_at IS NULL ORDER BY order_id, version DESC
    ), ref AS (
      SELECT opc.order_id, COALESCE(SUM(r.amount),0) AS refunded
      FROM order_payment_collection opc
      JOIN payment p ON p.payment_collection_id = opc.payment_collection_id
      JOIN refund r  ON r.payment_id = p.id AND r.deleted_at IS NULL
      GROUP BY opc.order_id
    )
    SELECT o.id, o.display_id, o.created_at, o.email,
           o.metadata->>'content_name' AS content_name,
           o.metadata->>'is_ppu' AS is_ppu,
           o.metadata->>'original_order_id' AS original_order_id,
           (ls.totals->>'paid_total')::numeric AS paid_total,
           COALESCE(ref.refunded,0)::numeric   AS refunded,
           li.id AS line_id, li.title AS line_title, li.variant_barcode AS barcode,
           oi.quantity AS qty, p.metadata->'bundle_items' AS bundle_items
    FROM "order" o
    JOIN ls ON ls.order_id = o.id
    LEFT JOIN ref ON ref.order_id = o.id
    LEFT JOIN order_item oi      ON oi.order_id = o.id
    LEFT JOIN order_line_item li ON li.id = oi.item_id
    LEFT JOIN product p          ON p.id = li.product_id
    WHERE o.deleted_at IS NULL AND o.created_at >= $1::timestamptz
    ORDER BY o.created_at;
  `, [since]);

  const orders = new Map();
  for (const r of rows) {
    let o = orders.get(r.id);
    if (!o) {
      o = { id: r.id, display_id: r.display_id, created_at: r.created_at, email: r.email,
            content_name: r.content_name, is_ppu: r.is_ppu === "true",
            original_order_id: r.original_order_id,
            paid_total: Number(r.paid_total || 0), refunded: Number(r.refunded || 0),
            lines: new Map() };
      orders.set(r.id, o);
    }
    if (r.line_id && !o.lines.has(r.line_id))
      o.lines.set(r.line_id, { title: r.line_title, barcode: r.barcode,
        qty: Number(r.qty || 1), bundle_items: r.bundle_items });
  }

  const classify = (cn, ppu) => ppu ? "ppu"
    : !cn ? "funnel"
    : cn.endsWith("_Catalog") ? "catalog"
    : cn.endsWith("_Purchase") ? "funnel"
    : (cn.endsWith("_Upsell") || cn === "Upsell") ? "ppu" : "funnel";

  const out = [];
  for (const o of orders.values()) {
    const pb_isbns = []; let has_ebook = false;
    for (const ln of o.lines.values()) {
      const bi = Array.isArray(ln.bundle_items) ? ln.bundle_items : null;
      const push = (bc) => { bc = (bc || "").replace(/-/g, "");
        if (ISBN.test(bc)) for (let i = 0; i < ln.qty; i++) pb_isbns.push(bc); else has_ebook = true; };
      if (bi) bi.forEach((it) => push(it.barcode)); else push(ln.barcode);
    }
    out.push({ id: o.id, display_id: o.display_id, created_at: o.created_at,
      email: o.email, content_name: o.content_name,
      class: classify(o.content_name, o.is_ppu), original_order_id: o.original_order_id,
      revenue: Number((o.paid_total - o.refunded).toFixed(2)),
      gross: o.paid_total, refunded: o.refunded,
      pb_isbns, pb_count: pb_isbns.length, has_ebook, n_lines: o.lines.size,
      lines_raw: [...o.lines.values()].map((l) => ({ title: l.title, barcode: l.barcode, qty: l.qty,
        bundle: Array.isArray(l.bundle_items) ? l.bundle_items.map((b) => b.barcode || b.title) : null })) });
  }
  console.log(JSON.stringify(out));
  await c.end();
})().catch((e) => { console.error("ERR " + e.message); process.exit(1); });
