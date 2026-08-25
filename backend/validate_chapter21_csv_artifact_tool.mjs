#!/usr/bin/env node

/**
 * Independently import every Chapter 21 / catalog-v1.9 CSV with
 * @oai/artifact-tool and verify its manifest-declared data-row count.
 *
 * Set ARTIFACT_TOOL_MODULE to the absolute path of artifact_tool.mjs.
 */

import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath, pathToFileURL } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.dirname(scriptDir);
const artifactToolModule = process.env.ARTIFACT_TOOL_MODULE;

if (!artifactToolModule) {
  throw new Error(
    "ARTIFACT_TOOL_MODULE must name the absolute artifact_tool.mjs path",
  );
}

const { Workbook } = await import(pathToFileURL(artifactToolModule).href);

const datasetDirs = [
  "backend/mt21",
  "backend/mt211",
  "backend/mt212",
  "backend/mt213",
  "backend/mt214",
  "backend/mt215",
  "backend/mt216",
  "backend/catalog-v1.9",
];

function parseManifest(text, manifestPath) {
  const lines = text.trimEnd().split(/\r?\n/);
  if (lines.shift() !== "path\tbytes\tsha256\tdata_rows") {
    throw new Error(`Unexpected manifest header: ${manifestPath}`);
  }
  return lines.map((line) => {
    const [relativePath, bytes, sha256, dataRows] = line.split("\t");
    return {
      relativePath,
      bytes: Number(bytes),
      sha256,
      dataRows: dataRows === "" ? null : Number(dataRows),
    };
  });
}

function importedRowCount(sheet) {
  const usedRange = sheet.getUsedRange(true);
  if (!usedRange) {
    return 0;
  }
  const values = usedRange.values;
  if (!Array.isArray(values) || values.length === 0) {
    return 0;
  }
  const hasNonemptyCell = values.some((row) =>
    row.some((value) => value !== null && value !== undefined && value !== ""),
  );
  if (!hasNonemptyCell) {
    return 0;
  }
  return values.length - 1;
}

let importedFileCount = 0;
let importedDataRowCount = 0;
let importedByteCount = 0;

for (const datasetDir of datasetDirs) {
  const manifestPath = path.join(repositoryRoot, datasetDir, "MANIFEST.tsv");
  const entries = parseManifest(
    await fs.readFile(manifestPath, "utf8"),
    manifestPath,
  );
  for (const entry of entries) {
    // Only schema-materialized record tables carry a manifest data-row
    // count.  Versioned CSV provenance snapshots are opaque resources whose
    // bytes and hashes are checked by the backend validator; they are not
    // catalog tables and must not be reinterpreted as such here.
    if (!entry.relativePath.endsWith(".csv") || entry.dataRows === null) {
      continue;
    }
    const csvPath = path.join(repositoryRoot, entry.relativePath);
    const csvText = await fs.readFile(csvPath, "utf8");
    const workbook = await Workbook.fromCSV(csvText, { sheetName: "Data" });
    const worksheet = workbook.worksheets.getItem("Data");
    const observedDataRows = importedRowCount(worksheet);
    if (observedDataRows !== entry.dataRows) {
      throw new Error(
        `${entry.relativePath}: manifest=${entry.dataRows}, imported=${observedDataRows}`,
      );
    }
    importedFileCount += 1;
    importedDataRowCount += observedDataRows;
    importedByteCount += Buffer.byteLength(csvText, "utf8");
  }
}

process.stdout.write(
  `${JSON.stringify({
    pass: true,
    importer: "@oai/artifact-tool",
    datasetDirectories: datasetDirs.length,
    csvFiles: importedFileCount,
    dataRows: importedDataRowCount,
    bytes: importedByteCount,
  })}\n`,
);
