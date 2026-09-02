export type GlyphSystem = {
  key: string;
  label: string;
  context: string;
  primaryFont: string;
  fontFamily: string;
  codepoints: number[];
  displayBasis: string;
  sourceUrl: string;
};

export type GlyphRecord = {
  id: string;
  systemKey: string;
  systemLabel: string;
  context: string;
  codepoint: number;
  char: string;
  unicodeLabel: string;
  primaryFont: string;
  fontFamily: string;
  displayBasis: string;
  sourceUrl: string;
  atlasOrder: number;
};

const greekCodepoints = [
  0x0391, 0x0392, 0x0393, 0x0394, 0x0395,
  0x0396, 0x0397, 0x0398, 0x0399, 0x039A,
  0x039B, 0x039C, 0x039D, 0x039E, 0x039F,
  0x03A0, 0x03A1, 0x03A3, 0x03A4, 0x03A5,
  0x03A6, 0x03A7, 0x03A8, 0x03A9, 0x03D8,
];

const mathCodepoints = [
  0x002B, 0x2212, 0x00D7, 0x00F7, 0x003D,
  0x2260, 0x2248, 0x221E, 0x221A, 0x2211,
  0x220F, 0x222B, 0x2202, 0x2207, 0x2208,
  0x2209, 0x222A, 0x2229, 0x2282, 0x2283,
  0x2227, 0x2228, 0x2192, 0x21D2, 0x2200,
];

export const GLYPH_SYSTEMS: GlyphSystem[] = [
  {
    key: "egyptian",
    label: "Egyptian hieroglyphs",
    context: "Egypt · standardized hieroglyph repertoire",
    primaryFont: "Noto Sans Egyptian Hieroglyphs",
    fontFamily: '"Noto Sans Egyptian Hieroglyphs", "Segoe UI Historic", serif',
    codepoints: [
      0x13000, 0x13001, 0x13002, 0x13003, 0x13004,
      0x13005, 0x13006, 0x13007, 0x13008, 0x13009,
      0x1300A, 0x1300B, 0x1300C, 0x1300D, 0x1300E,
      0x1300F, 0x13010, 0x13011, 0x13012, 0x13013,
      0x13014, 0x13015, 0x13016, 0x13017, 0x13018,
    ],
    displayBasis: "Unicode standardized sign form; not a physical archaeological witness.",
    sourceUrl: "https://www.unicode.org/charts/PDF/U13000.pdf",
  },
  {
    key: "cuneiform",
    label: "Cuneiform",
    context: "Mesopotamia · standardized cuneiform sign repertoire",
    primaryFont: "Noto Sans Cuneiform",
    fontFamily: '"Noto Sans Cuneiform", "Segoe UI Historic", serif',
    codepoints: [
      0x12000, 0x12001, 0x12002, 0x12003, 0x12004,
      0x12005, 0x12006, 0x12007, 0x12008, 0x12009,
      0x1200A, 0x1200B, 0x1200C, 0x1200D, 0x1200E,
      0x1200F, 0x12010, 0x12011, 0x12012, 0x12013,
      0x12014, 0x12015, 0x12016, 0x12017, 0x12018,
    ],
    displayBasis: "Unicode standardized sign form; not a tablet-specific impression.",
    sourceUrl: "https://www.unicode.org/charts/PDF/U12000.pdf",
  },
  {
    key: "linear-a",
    label: "Linear A",
    context: "Aegean · standardized Linear A sign repertoire",
    primaryFont: "Noto Sans Linear A",
    fontFamily: '"Noto Sans Linear A", "Segoe UI Historic", serif',
    codepoints: [
      0x10600, 0x10601, 0x10602, 0x10603, 0x10604,
      0x10605, 0x10606, 0x10607, 0x10608, 0x10609,
      0x1060A, 0x1060B, 0x1060C, 0x1060D, 0x1060E,
      0x1060F, 0x10610, 0x10611, 0x10612, 0x10613,
      0x10614, 0x10615, 0x10616, 0x10617, 0x10618,
    ],
    displayBasis: "Unicode standardized sign form; not a physical inscription witness.",
    sourceUrl: "https://www.unicode.org/charts/PDF/U10600.pdf",
  },
  {
    key: "linear-b",
    label: "Linear B",
    context: "Aegean · standardized Linear B syllabary",
    primaryFont: "Noto Sans Linear B",
    fontFamily: '"Noto Sans Linear B", "Segoe UI Historic", serif',
    codepoints: [
      0x10000, 0x10001, 0x10002, 0x10003, 0x10004,
      0x10005, 0x10006, 0x10007, 0x10008, 0x10009,
      0x1000A, 0x1000B, 0x1000D, 0x1000E, 0x1000F,
      0x10010, 0x10011, 0x10012, 0x10013, 0x10014,
      0x10015, 0x10016, 0x10017, 0x10018, 0x10019,
    ],
    displayBasis: "Unicode standardized sign form; not a tablet-specific witness.",
    sourceUrl: "https://www.unicode.org/charts/PDF/U10000.pdf",
  },
  {
    key: "phoenician",
    label: "Phoenician",
    context: "Eastern Mediterranean · standardized Phoenician repertoire",
    primaryFont: "Noto Sans Phoenician",
    fontFamily: '"Noto Sans Phoenician", "Segoe UI Historic", serif',
    codepoints: [
      0x10900, 0x10901, 0x10902, 0x10903, 0x10904,
      0x10905, 0x10906, 0x10907, 0x10908, 0x10909,
      0x1090A, 0x1090B, 0x1090C, 0x1090D, 0x1090E,
      0x1090F, 0x10910, 0x10911, 0x10912, 0x10913,
      0x10914, 0x10915, 0x10916, 0x10917, 0x10918,
    ],
    displayBasis: "Unicode standardized sign form; not an inscription-specific ductus.",
    sourceUrl: "https://www.unicode.org/charts/PDF/U10900.pdf",
  },
  {
    key: "greek",
    label: "Greek",
    context: "Mediterranean · uppercase Greek + archaic koppa display sample",
    primaryFont: "Noto Serif",
    fontFamily: '"Noto Serif", Georgia, serif',
    codepoints: greekCodepoints,
    displayBasis: "Unicode display forms. This v0 sample does not yet separate archaic local alphabets.",
    sourceUrl: "https://www.unicode.org/charts/PDF/U0370.pdf",
  },
  {
    key: "brahmi",
    label: "Brahmi",
    context: "South Asia · standardized Brahmi repertoire",
    primaryFont: "Noto Sans Brahmi",
    fontFamily: '"Noto Sans Brahmi", serif',
    codepoints: [
      0x11003, 0x11004, 0x11005, 0x11006, 0x11007,
      0x11008, 0x11009, 0x1100A, 0x1100B, 0x1100C,
      0x1100D, 0x1100E, 0x1100F, 0x11010, 0x11011,
      0x11012, 0x11013, 0x11014, 0x11015, 0x11016,
      0x11017, 0x11018, 0x11019, 0x1101A, 0x1101B,
    ],
    displayBasis: "Unicode standardized sign form; not inscription-specific stroke evidence.",
    sourceUrl: "https://www.unicode.org/charts/PDF/U11000.pdf",
  },
  {
    key: "runic",
    label: "Runic",
    context: "Northern Europe · broad Unicode runic sample",
    primaryFont: "Noto Sans Runic",
    fontFamily: '"Noto Sans Runic", "Segoe UI Historic", serif',
    codepoints: [
      0x16A0, 0x16A1, 0x16A2, 0x16A3, 0x16A4,
      0x16A5, 0x16A6, 0x16A7, 0x16A8, 0x16A9,
      0x16AA, 0x16AB, 0x16AC, 0x16AD, 0x16AE,
      0x16AF, 0x16B0, 0x16B1, 0x16B2, 0x16B3,
      0x16B4, 0x16B5, 0x16B6, 0x16B7, 0x16B8,
    ],
    displayBasis: "Unicode standardized runic forms; not yet restricted to Elder Futhark witnesses.",
    sourceUrl: "https://www.unicode.org/charts/PDF/U16A0.pdf",
  },
  {
    key: "ogham",
    label: "Ogham",
    context: "Ireland and Britain · standardized Ogham repertoire",
    primaryFont: "Noto Sans Ogham",
    fontFamily: '"Noto Sans Ogham", "Segoe UI Historic", serif',
    codepoints: [
      0x1681, 0x1682, 0x1683, 0x1684, 0x1685,
      0x1686, 0x1687, 0x1688, 0x1689, 0x168A,
      0x168B, 0x168C, 0x168D, 0x168E, 0x168F,
      0x1690, 0x1691, 0x1692, 0x1693, 0x1694,
      0x1695, 0x1696, 0x1697, 0x1698, 0x1699,
    ],
    displayBasis: "Unicode standardized Ogham forms; not stone-specific incision evidence.",
    sourceUrl: "https://www.unicode.org/charts/PDF/U1680.pdf",
  },
  {
    key: "hebrew",
    label: "Hebrew",
    context: "Levant / Jewish textual tradition · square Hebrew display sample",
    primaryFont: "Noto Sans Hebrew",
    fontFamily: '"Noto Sans Hebrew", "Arial Hebrew", serif',
    codepoints: [
      0x05D0, 0x05D1, 0x05D2, 0x05D3, 0x05D4,
      0x05D5, 0x05D6, 0x05D7, 0x05D8, 0x05D9,
      0x05DA, 0x05DB, 0x05DC, 0x05DD, 0x05DE,
      0x05DF, 0x05E0, 0x05E1, 0x05E2, 0x05E3,
      0x05E4, 0x05E5, 0x05E6, 0x05E7, 0x05E8,
    ],
    displayBasis: "Modern Unicode square-letter display forms. Raw manuscript marks remain a separate evidence layer.",
    sourceUrl: "https://www.unicode.org/charts/PDF/U0590.pdf",
  },
  {
    key: "kangxi",
    label: "Chinese radicals",
    context: "East Asia · Kangxi radical structural proxy",
    primaryFont: "Noto Serif SC",
    fontFamily: '"Noto Serif SC", "Songti SC", "Hiragino Mincho ProN", serif',
    codepoints: [
      0x2F00, 0x2F01, 0x2F02, 0x2F03, 0x2F04,
      0x2F05, 0x2F06, 0x2F07, 0x2F08, 0x2F09,
      0x2F0A, 0x2F0B, 0x2F0C, 0x2F0D, 0x2F0E,
      0x2F0F, 0x2F10, 0x2F11, 0x2F12, 0x2F13,
      0x2F14, 0x2F15, 0x2F16, 0x2F17, 0x2F18,
    ],
    displayBasis: "Kangxi radicals are a display-engineering proxy, not oracle-bone evidence.",
    sourceUrl: "https://www.unicode.org/charts/PDF/U2F00.pdf",
  },
  {
    key: "math",
    label: "Mathematical notation",
    context: "Cross-cultural formal notation · selected operators",
    primaryFont: "Noto Serif",
    fontFamily: '"STIX Two Math", "Cambria Math", "Noto Serif", serif',
    codepoints: mathCodepoints,
    displayBasis: "Modern standardized mathematical symbols used as a non-script comparison set.",
    sourceUrl: "https://www.unicode.org/charts/",
  },
];

export const GLYPHS: GlyphRecord[] = GLYPH_SYSTEMS.flatMap((system, systemIndex) =>
  system.codepoints.slice(0, 25).map((codepoint, glyphIndex) => {
    const atlasOrder = systemIndex * 25 + glyphIndex + 1;
    return {
      id: `G${String(atlasOrder).padStart(5, "0")}`,
      systemKey: system.key,
      systemLabel: system.label,
      context: system.context,
      codepoint,
      char: String.fromCodePoint(codepoint),
      unicodeLabel: `U+${codepoint.toString(16).toUpperCase().padStart(4, "0")}`,
      primaryFont: system.primaryFont,
      fontFamily: system.fontFamily,
      displayBasis: system.displayBasis,
      sourceUrl: system.sourceUrl,
      atlasOrder,
    };
  }),
);
