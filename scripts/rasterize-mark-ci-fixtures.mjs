import fs from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";

const manifestList = (process.env.MARK_FIXTURE_MANIFESTS ?? "")
  .split(",")
  .map(value => value.trim())
  .filter(Boolean);
const outDir = process.env.MARK_FIXTURE_RASTER_OUT ?? "artifacts/mark-v7-ci-raster-fixtures";

if (!manifestList.length) throw new Error("MARK_FIXTURE_MANIFESTS is required");

await fs.mkdir(path.join(outDir, "images"), { recursive: true });
const generated = [];

for (const manifestPath of manifestList) {
  const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
  if (manifest.schema !== "mark_harvest_manifest_v1") {
    throw new Error(`unsupported fixture manifest ${manifest.schema}: ${manifestPath}`);
  }

  const clone = structuredClone(manifest);
  for (const [index, source] of clone.sources.entries()) {
    const original = manifest.sources[index];
    const imagePath = original?.capture?.imagePath;
    if (!imagePath) continue;

    const input = path.resolve(path.dirname(manifestPath), imagePath);
    const extension = path.extname(input).toLowerCase();
    if (extension !== ".svg") continue;

    const stem = `${path.basename(manifestPath, path.extname(manifestPath))}-${String(index + 1).padStart(3, "0")}`;
    const outputName = `${stem}.png`;
    const output = path.join(outDir, "images", outputName);
    await sharp(input, { density: 144 }).png({ compressionLevel: 9 }).toFile(output);

    source.capture.imagePath = `images/${outputName}`;
    source.context = {
      ...(source.context ?? {}),
      ciRasterFixture: {
        sourceFormat: "svg",
        compilerFormat: "png",
        density: 144,
      },
    };
  }

  const generatedPath = path.join(outDir, path.basename(manifestPath));
  await fs.writeFile(generatedPath, `${JSON.stringify(clone, null, 2)}\n`);
  generated.push(generatedPath);
}

await fs.writeFile(
  path.join(outDir, "generated-manifests.txt"),
  `${generated.join("\n")}\n`,
);
console.log(`Rasterized ${generated.length} Mark CI fixture manifests for the Rust compiler`);
