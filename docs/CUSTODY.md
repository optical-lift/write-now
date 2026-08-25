# Write Now Source-Control Custody

## Authority

This repository owns the Write Now Publishing House application and publishing-engine code.

It does not own the executable migration history of the shared `noel-core` Supabase project. That authority belongs to `optical-lift/noel-core-db`.

## Product boundary

Write Now owns:

- reader and research web surfaces
- publishing-domain models and validators
- reconstruction workflows
- renderers for web, EPUB, PDF, print, and audio derivatives
- bibliographic and library metadata generation
- the governed bridge that consumes frozen Noel research packets

Write Now does not own:

- Noel's provisional research state
- Atlas application state or code
- the shared Supabase project's migration ledger

## Dependency direction

Application surfaces must depend on Write Now domain interfaces, not on Noel/Core database internals.

Allowed direction:

```text
app
  -> Write Now domain
  -> governed Noel bridge when necessary
  -> published/read API boundary
```

Forbidden direction:

```text
app
  -> core.manuscript_registry
app
  -> core.text_witness_registry
app
  -> arbitrary Noel research tables
```

Noel research enters publication custody only through a frozen, versioned, provenance-bearing research packet or an explicitly governed bridge contract.

## Database ownership

The shared Supabase project may contain multiple product schemas, including `core`, `atlas`, `wnph`, and `wnph_api`.

Schema separation does not create separate migration authorities. All executable DDL for that physical Supabase project must ultimately be source-controlled through `optical-lift/noel-core-db`.

## Public attribution firewall

Research/transmission metadata may never silently rewrite public authorship, title-page credit, ISBN metadata, ONIX contributors, MARC primary creator, audiobook attribution, or copyright statements.

## Promotion rule

Do not create a generic shared package merely because two products appear similar. Promote a primitive only after multiple products demonstrably share the same semantics and custody requirements.
