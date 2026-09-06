import { build } from "esbuild";
import postcss from "postcss";
import tailwind from "@tailwindcss/postcss";
import fs from "node:fs/promises";
import crypto from "node:crypto";
const out = "../nbn/desk_assets";
await build({
  entryPoints: ["app/main.tsx"],
  bundle: true,
  minify: true,
  format: "iife",
  target: "es2022",
  outfile: `${out}/workspace.js`,
  loader: { ".png": "dataurl" },
  define: { "process.env.NODE_ENV": '"production"' },
  legalComments: "eof",
  sourcemap: false,
});
const result = await postcss([tailwind()]).process(
  (await fs.readFile("app/globals.css", "utf8")) +
    "\n" +
    (await fs.readFile("app/production.css", "utf8")),
  { from: "app/globals.css", to: `${out}/workspace.css` },
);
await fs.writeFile(`${out}/workspace.css`, result.css);
const manifest = {};
for (const name of ["workspace.js", "workspace.css"])
  manifest[name] = crypto
    .createHash("sha256")
    .update(await fs.readFile(`${out}/${name}`))
    .digest("hex");
await fs.writeFile(
  `${out}/workspace-manifest.json`,
  JSON.stringify(manifest, null, 2) + "\n",
);
console.log(
  "Built static Desk assets; Python remains the only production runtime.",
);
