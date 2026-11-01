/* Obtiene solo metadatos del catálogo en vivo: categoría, nombre, código y logo.
   No solicita ni guarda URL de reproducción ni tokens/licencias de streams. */
"use strict";
const fs = require("fs");
const path = require("path");
const magis = require("./xuper/magis.js");

const OUTPUT = process.env.OUTPUT_FILE || "canales_xuper.json";
const PAGE_SIZE = 50;
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

function callbackCall(fn, ...args) {
  return new Promise((resolve, reject) => {
    fn(...args, (err, ...result) => err ? reject(err) : resolve(result));
  });
}

async function main() {
  console.log("Consultando categorías de TV en vivo de XuperTV…");
  const [categories] = await callbackCall(magis.getLiveCategories);
  const outputCategories = [];
  const allChannels = [];
  const seen = new Set();

  for (const cat of categories || []) {
    const category = {
      id: String(cat.id || ""),
      name: String(cat.name || "Sin categoría"),
      code: String(cat.code || "")
    };
    outputCategories.push(category);
    console.log(`Categoría: ${category.name}`);

    for (let page = 1; page <= 100; page++) {
      const [channels, hasMore] = await callbackCall(
        magis.getLiveChannels, category.id, page, PAGE_SIZE
      );
      let addedOnPage = 0;
      for (const ch of channels || []) {
        const code = String(ch.channelCode || "");
        if (!code || seen.has(`${category.id}:${code}`)) continue;
        seen.add(`${category.id}:${code}`);
        allChannels.push({
          categoryId: category.id,
          category: category.name,
          channelCode: code,
          name: String(ch.name || "Canal sin nombre"),
          number: ch.index ?? null,
          logo: String(ch.logo || ""),
          uhd: Boolean(ch.uhd),
          source: "XuperTV"
        });
        addedOnPage++;
      }
      console.log(`  página ${page}: ${addedOnPage} canales`);
      if (!hasMore || !channels || channels.length === 0) break;
      await delay(500);
    }
    await delay(500);
  }

  const result = {
    source: "XuperTV",
    updatedAt: new Date().toISOString(),
    categoryCount: outputCategories.length,
    channelCount: allChannels.length,
    categories: outputCategories,
    channels: allChannels
  };
  fs.writeFileSync(OUTPUT, JSON.stringify(result, null, 2) + "\n", "utf8");
  console.log(`Guardado ${OUTPUT}: ${allChannels.length} canales en ${outputCategories.length} categorías.`);
}

main().catch(err => {
  console.error("No se pudo obtener el catálogo:", err && err.message ? err.message : err);
  process.exit(1);
});
