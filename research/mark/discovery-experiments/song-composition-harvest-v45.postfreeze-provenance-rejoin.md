# V45 post-freeze provenance rejoin — CR-001 semantic bridge audit

**Experiment:** `mark:song-composition-harvest:v45`  
**Phase-A freeze:** `3ab58910b60b90c7bb682788e742503feeb5f329`  
**Status:** post-freeze contextual audit; does not alter any V45 Phase-A status  
**Date:** 2026-09-18

## Purpose

After the blind V45 Phase-A freeze existed, provenance was reopened only to answer the Song compiler handoff question:

> Does the strongest harvested physical composition rule already have enough source-grounded specificity to justify a Song semantic/compiler mapping?

This audit does not refit V45, change a candidate, add a witness to the frozen Phase-A packet, or reinterpret the held-out score.

## Custody rejoin

The V5 source pixels came from GitHub Actions run `33755743472`, artifact:

- `mark-source-rule-atlas-v1-sealed-evidence`
- artifact id `9893738364`
- artifact digest `sha256:5aee2d958875d711a148e08c37c613457eeb734efc8e2c773fa63782faad1a20`

The parallel frozen context rejoin was:

- `mark-source-rule-atlas-v1-context-rejoin`
- artifact id `9894817556`
- artifact digest `sha256:6eaa3c9093b0c0a668be828dd07d22e4d20111adc350b2878a881d7c1056fc4e`

Its contract states that source custody and institutional provenance were rejoined after blind scoring without changing blind rows, ranks, or counts.

## CR-001 capped positive-witness rejoin

The six positive witnesses emitted by the frozen V45 runner map to six different Bavarian State Library / Munich Digitization Centre source objects. All are canvas 1 captures from the already-frozen BSB holdout feed.

1. `S000CD9B9CDAB347F` / `SRC00328`
   - Pius Manzador, *Deren Predigen...*
   - observation `O44C9E8D8B07ECAD8`
   - region `x=95 y=4 w=62 h=100`
   - exact frozen pixels show the four-center path in worn/blemished binding surface, not a written character.

2. `S08D2070B1CF8C96A` / `SRC00441`
   - Pierre Besse, *Conciones, Siue Conceptvs Theologici Ac Praedicabiles. T.2...*
   - observation `O00A018ECA43E13AD`
   - region `x=21 y=92 w=301 h=290`
   - exact frozen pixels show the four-center path running along the stroke of a printed Latin `C`.

3. `S0B6FA01FD1099102` / `SRC00263`
   - Johann Anton Kravogl, *Sittliche Unterweisungen...*
   - observation `O1A4B4371CD80063E`
   - region `x=779 y=146 w=255 h=370`
   - exact frozen pixels show the path inside a cover stain/blemish rather than a written sign.

4. `S0CAB21465D8F6499` / `SRC00294`
   - *Lob- und Ehren-Ruff Deren Heiligen Gottes...*
   - observation `O76B9FE127CE909D6`
   - region `x=65 y=286 w=177 h=1194`
   - exact frozen pixels place the path in decorative binding/cover linework.

5. `S0D633626914D3E68` / `SRC00323`
   - Michael Lochmair, *Parochiale Curatorum*
   - observation `O6F122131F16DFA29`
   - region `x=641 y=164 w=124 h=449`
   - exact frozen pixels place the path on a heavy horizontal illustration/border stroke adjacent to ornament.

6. `S0F72C82E0B89E1E4` / `SRC00334`
   - Angelo Maria Marchesini, *Geistlicher Herold. 1*
   - observation `O734AA2E84237F3E5`
   - region `x=582 y=272 w=111 h=110`
   - exact frozen pixels show the path in faint surface texture rather than a written character.

The visual classifications above are post-freeze descriptive inspection of the exact frozen pixels. They are not added to the V45 scoring model.

## Interpretation boundary

This provenance audit **does not weaken or reverse CR-001's Phase-A status**.

CR-001 remains `HARVESTED_RULE`: the frozen anonymous physical/topological operator composition transferred under the preregistered tests.

What the rejoin changes is the next inference boundary.

Because the same harvested rule is visibly instantiated in semantically heterogeneous material—including non-symbolic wear, stains, decorative linework, illustration borders, surface texture, and at least one printed character—the current evidence does **not** justify any claim that CR-001 is:

- a glyph meaning;
- a lexical operation;
- a specific Song RELATION family;
- a specific Song EVENT/operator macro;
- a temporal sequence relation;
- a causal relation;
- or a decoder-specific semantic rule.

The strongest supported post-freeze statement is narrower:

> CR-001 is a transferable first-order composition law over the frozen anonymous physical graph representation. Its specificity to symbolic/semantic structure has not yet been established.

## Song handoff consequence

The first Song handoff must therefore preserve CR-001 as an **unresolved semantic bridge**, not promote it to a named Song composition rule.

A subsequent experiment must distinguish:

`generic physical graph compositionality`

from

`symbol-bearing structural compositionality with a predictable Song delta`.

That experiment must be preregistered before semantic-bearing versus non-semantic controls are scored. It may not retroactively change the V45 result.
