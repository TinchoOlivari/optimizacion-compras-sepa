import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";

import { describe, expect, it } from "vitest";

const SRC_ROOT = join(import.meta.dirname);
const PAGES_DIR = join(SRC_ROOT, "pages");

function collectSourceFiles(dir: string, acc: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const fullPath = join(dir, entry);
    const stat = statSync(fullPath);
    if (stat.isDirectory()) {
      if (entry === "node_modules") continue;
      collectSourceFiles(fullPath, acc);
      continue;
    }
    if (/\.(tsx?|jsx?)$/.test(entry) && !entry.endsWith(".test.ts") && !entry.endsWith(".test.tsx")) {
      acc.push(fullPath);
    }
  }
  return acc;
}

function pageFiles(): string[] {
  return collectSourceFiles(PAGES_DIR).filter((file) => !file.endsWith(".test.tsx"));
}

function rel(path: string): string {
  return relative(SRC_ROOT, path);
}

describe("architecture guard — páginas delgadas", () => {
  it("no importan @/lib/api ni declaran queryKey/useQuery/useMutation", () => {
    const violations: string[] = [];

    for (const file of pageFiles()) {
      const content = readFileSync(file, "utf8");
      if (/from\s+["']@\/lib\/api["']/.test(content)) {
        violations.push(`${rel(file)}: import directo de @/lib/api`);
      }
      if (/\buseQuery\s*\(/.test(content)) {
        violations.push(`${rel(file)}: useQuery en página`);
      }
      if (/\buseMutation\s*\(/.test(content)) {
        violations.push(`${rel(file)}: useMutation en página`);
      }
      if (/queryKey:\s*\[/.test(content)) {
        violations.push(`${rel(file)}: queryKey literal en página`);
      }
    }

    expect(violations).toEqual([]);
  });
});

describe("architecture guard — query keys por dominio", () => {
  const DOMAIN_KEY_PATTERNS = [
    /queryKey:\s*\[\s*["']preferencias["']/,
    /queryKey:\s*\[\s*["']catalogo["']/,
    /queryKey:\s*\[\s*["']carritos["']/,
    /queryKey:\s*\[\s*["']buscar-productos["']/,
    /queryKey:\s*\[\s*["']producto-detalle["']/,
  ];

  it("no hay keys literales de dominio migrado fuera de features/", () => {
    const violations: string[] = [];
    const outsideFeatures = collectSourceFiles(SRC_ROOT).filter(
      (file) => !file.includes("/features/"),
    );

    for (const file of outsideFeatures) {
      if (file.endsWith(".test.ts") || file.endsWith(".test.tsx")) continue;
      const content = readFileSync(file, "utf8");
      for (const pattern of DOMAIN_KEY_PATTERNS) {
        if (pattern.test(content)) {
          violations.push(`${rel(file)}: ${pattern}`);
        }
      }
    }

    expect(violations).toEqual([]);
  });
});

describe("architecture guard — módulos de query keys", () => {
  it("cada feature migrada expone queryKeys.ts", () => {
    const features = ["carrito", "preferencias", "catalogo"] as const;
    const missing = features.filter(
      (feature) =>
        !existsSync(join(SRC_ROOT, "features", feature, "lib", "queryKeys.ts")),
    );
    expect(missing).toEqual([]);
  });
});
