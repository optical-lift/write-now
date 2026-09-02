import type { Metadata } from "next";
import GlyphAtlasClient from "./GlyphAtlasClient";
import "./glyph-atlas.css";

export const metadata: Metadata = {
  title: "Glyph Atlas v0 · Write Now",
  description: "A blind computational comparison wall for 300 standardized glyph display forms.",
};

export default function GlyphAtlasPage() {
  return <GlyphAtlasClient />;
}
