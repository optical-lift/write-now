import fs from 'node:fs';
import path from 'node:path';

const root = path.join(process.cwd(), 'research', 'corpus-packets');

if (!fs.existsSync(root)) {
  console.log('No research/corpus-packets directory yet.');
  process.exit(0);
}

const files = fs.readdirSync(root).filter((name) => name.endsWith('.json')).sort();
if (files.length === 0) {
  throw new Error('research/corpus-packets exists but contains no JSON packets');
}

for (const file of files) {
  const fullPath = path.join(root, file);
  const packet = JSON.parse(fs.readFileSync(fullPath, 'utf8'));

  if (packet.packetType !== 'creator_corpus_empirical_schema_test') {
    throw new Error(`${file}: unexpected packetType`);
  }
  if (packet.status !== 'research_packet_not_canonical_database_state') {
    throw new Error(`${file}: packet must remain explicitly non-canonical`);
  }
  if (!packet.creator?.provisionalId || !packet.creator?.canonicalName) {
    throw new Error(`${file}: missing creator identity`);
  }

  const sourceIds = new Set((packet.sourceRegistry ?? []).map((source) => source.sourceId));
  const attestationIds = new Set((packet.titleAttestations ?? []).map((attestation) => attestation.attestationId));
  const workIds = new Set((packet.historicalWorksEstablishedForSchemaTest ?? []).map((work) => work.provisionalId));

  if (sourceIds.size !== (packet.sourceRegistry ?? []).length) {
    throw new Error(`${file}: duplicate sourceId`);
  }
  if (attestationIds.size !== (packet.titleAttestations ?? []).length) {
    throw new Error(`${file}: duplicate attestationId`);
  }
  if (workIds.size !== (packet.historicalWorksEstablishedForSchemaTest ?? []).length) {
    throw new Error(`${file}: duplicate provisional work id`);
  }

  const requireSources = (owner, ids = []) => {
    for (const id of ids) {
      if (!sourceIds.has(id)) throw new Error(`${file}: ${owner} references unknown source ${id}`);
    }
  };
  const requireAttestations = (owner, ids = []) => {
    for (const id of ids) {
      if (!attestationIds.has(id)) throw new Error(`${file}: ${owner} references unknown attestation ${id}`);
    }
  };

  for (const claim of packet.creator.nameClaims ?? []) {
    requireSources(`creator.nameClaims:${claim.displayName}`, claim.evidenceSourceIds);
  }
  for (const membership of packet.sourceCircleMemberships ?? []) {
    requireSources(`sourceCircleMembership:${membership.provisionalId}`, membership.evidenceSourceIds);
    if (membership.publicAttributionEffect !== 'none') {
      throw new Error(`${file}: source-circle membership may not change public attribution`);
    }
  }
  for (const attestation of packet.titleAttestations ?? []) {
    if (!sourceIds.has(attestation.sourceId)) {
      throw new Error(`${file}: attestation ${attestation.attestationId} references unknown source ${attestation.sourceId}`);
    }
  }
  for (const adjudication of packet.workIdentityAdjudications ?? []) {
    requireAttestations(`adjudication:${adjudication.provisionalId}`, adjudication.attestationIds);
  }
  for (const work of packet.historicalWorksEstablishedForSchemaTest ?? []) {
    requireAttestations(`work:${work.provisionalId}`, work.attestationIds);
    requireSources(`work:${work.provisionalId}`, work.evidenceSourceIds);
  }
  for (const series of packet.seriesRecords ?? []) {
    requireSources(`series:${series.provisionalId}`, series.evidenceSourceIds);
    requireAttestations(`series:${series.provisionalId}`, (series.members ?? []).map((member) => member.attestationId));
  }
  for (const cluster of packet.recoveryClusterCandidates ?? []) {
    for (const workId of cluster.memberWorkIds ?? []) {
      if (!workIds.has(workId)) throw new Error(`${file}: cluster ${cluster.provisionalId} references unknown work ${workId}`);
    }
    for (const workId of cluster.attachedBibliographicLossWorkIds ?? []) {
      if (!workIds.has(workId)) throw new Error(`${file}: cluster ${cluster.provisionalId} references unknown attached work ${workId}`);
    }
  }

  const declaredMinimum = packet.creatorCorpus?.minimumDistinctAttestationStringsInThisPacket ?? 0;
  const distinctTitleStrings = new Set((packet.titleAttestations ?? []).map((attestation) => attestation.displayedTitle)).size;
  if (distinctTitleStrings < declaredMinimum) {
    throw new Error(`${file}: declares at least ${declaredMinimum} distinct title strings but contains ${distinctTitleStrings}`);
  }

  console.log(`${file}: valid (${packet.titleAttestations.length} attestations, ${distinctTitleStrings} distinct title strings, ${packet.sourceRegistry.length} sources)`);
}
