"""Class 9 pins: lineage independence is a property of the SOURCE, never of the
locator a document was reached through or of the proposer's lineage label.

Found 2026-10-19 by hypothesis testing against v1.1.3: one SEC filing fetched
through two URL variants (/Archives/... and /ix?doc=/Archives/...) minted
CORROBORATED with "2 independent provenance-verified lineages"; two legacy
records carrying identical content under different model-chosen lineage_ids
counted as two supporting lineages.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from glass_ionomer.verify.admissibility import EvidenceRecord, admit
from glass_ionomer.verify.resolver import (
    FetchResult,
    Lead,
    _canonical_identity,
    make_http_resolver,
    resolve,
)
from glass_ionomer.verify.status import (
    AuthorityTier,
    Claim,
    Entailment,
    EvidenceStatus,
    VerifiabilityClass,
    decide_status,
)

NOW = datetime(2026, 10, 19, tzinfo=timezone.utc)
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm"
VIEWER = "https://www.sec.gov/ix?doc=/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm"
MOBILE = ARCHIVE + "?source=mobile"
CONTENT = ("Apple Inc. total net sales were $391,035 million for the fiscal year ended "
           "September 28, 2024.")


class IndependenceIdentityPins(unittest.TestCase):
    def test_url_variants_of_one_filing_share_one_identity(self):
        self.assertEqual(len({_canonical_identity(u) for u in (ARCHIVE, VIEWER, MOBILE)}), 1)

    def test_canonical_ids_are_untouched(self):
        self.assertEqual(_canonical_identity("https://doi.org/10.1000/xyz123?utm=1"), "doi:10.1000/xyz123")
        self.assertEqual(_canonical_identity("https://arxiv.org/abs/2401.00001#x"), "arxiv:2401.00001")
        self.assertEqual(_canonical_identity("https://pubmed.ncbi.nlm.nih.gov/123456/"), "pmid:123456")

    def test_one_document_two_urls_cannot_corroborate(self):
        def fetch(url):
            return FetchResult(content=CONTENT, final_url=url,
                               resolved_identity=_canonical_identity(url),
                               published=NOW - timedelta(days=5), source_type="url",
                               authority_tier=AuthorityTier.WEB)
        resolver = make_http_resolver(fetch=fetch, default_published=NOW - timedelta(days=5))
        leads = [Lead.suggest("L1", ARCHIVE, claimed_published=NOW, suggested_quote="391,035"),
                 Lead.suggest("L2", VIEWER, claimed_published=NOW, suggested_quote="391,035")]
        records, inadmissible = resolve(leads, resolver_fn=resolver)
        self.assertEqual(inadmissible, [])
        items = admit(records, now=NOW, max_age=timedelta(days=365),
                      entailment_fn=lambda _text: Entailment.ENTAILS)
        decision = decide_status(Claim("c", "net sales were $391,035 million",
                                       VerifiabilityClass.MECHANICAL), [], items, now=NOW)
        self.assertEqual(decision.support_lineages, 1, decision.reasons)
        self.assertNotEqual(decision.status, EvidenceStatus.CORROBORATED, decision.reasons)

    def test_two_genuinely_distinct_sources_still_count_as_two(self):
        def fetch(url):
            return FetchResult(content=CONTENT + f" [{url[-1]}]", final_url=url,
                               resolved_identity=_canonical_identity(url),
                               published=NOW - timedelta(days=5), source_type="url",
                               authority_tier=AuthorityTier.WEB)
        resolver = make_http_resolver(fetch=fetch, default_published=NOW - timedelta(days=5))
        leads = [Lead.suggest("L1", "https://a.example/report-a", claimed_published=NOW, suggested_quote="391,035"),
                 Lead.suggest("L2", "https://b.example/report-b", claimed_published=NOW, suggested_quote="391,035")]
        records, _ = resolve(leads, resolver_fn=resolver)
        items = admit(records, now=NOW, max_age=timedelta(days=365),
                      entailment_fn=lambda _text: Entailment.ENTAILS)
        decision = decide_status(Claim("c", "t", VerifiabilityClass.MECHANICAL), [], items, now=NOW)
        self.assertEqual(decision.support_lineages, 2, decision.reasons)

    def test_legacy_lineage_label_is_not_proposer_controlled(self):
        recs = [EvidenceRecord.of("model-lineage-1", CONTENT, published=NOW - timedelta(days=1)),
                EvidenceRecord.of("model-lineage-2", CONTENT, published=NOW - timedelta(days=1))]
        items = admit(recs, now=NOW, max_age=timedelta(days=365))
        decision = decide_status(Claim("c", "t", VerifiabilityClass.MECHANICAL), [], items, now=NOW)
        self.assertEqual(decision.support_lineages, 1, decision.reasons)


if __name__ == "__main__":
    unittest.main()
