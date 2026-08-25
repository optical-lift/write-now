# @write-now/noel-bridge

This package is the only Write Now application-code boundary that may understand Noel/Core research identifiers or frozen research packet contracts.

Its purpose is translation between research custody and publication custody.

It must not expose arbitrary `core.*` tables to the rest of the Write Now application. It should consume stable IDs, versioned packets, approved views/RPCs, and provenance-bearing adjudications.

A Noel hypothesis is never publication truth merely because this package can read it.
