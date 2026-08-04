"""Offline integrity + required-content checks for the enriched S01E01 graph.

These run against the seed JSON (no live database), so they are fast and always
runnable. They encode the integrity rules and required-content assertions from
the Episode 101 source-grounded enrichment task.
"""
from __future__ import annotations

import pytest

from spoilerless.app.graph.ontology import load_ontology
from spoilerless.app.graph.seed import load_seed_data, validate_seed

SRC = "dexter:source:s01e01"
EP = "dexter_s01e01"


@pytest.fixture(scope="module")
def data() -> dict:
    return load_seed_data()


@pytest.fixture(scope="module")
def ids(data) -> set[str]:
    out: set[str] = {data["series"]["id"]}
    for key in ("episodes", "characters", "events", "locations",
                "organizations", "objects", "claims", "sources", "evidence"):
        for row in data[key]:
            out.add(row["id"])
    return out


def _claim_labels(data) -> list[str]:
    return [c["label"] for c in data["claims"]]


def _has_claim(data, needle: str) -> bool:
    n = needle.lower()
    return any(n in label.lower() for label in _claim_labels(data))


def _node_labels(data, key: str) -> set[str]:
    return {r["label"] for r in data[key]}


# ── Ontology / referential integrity ──

def test_seed_validates_against_ontology(data):
    validate_seed(data, load_ontology())  # raises on any violation


def test_no_duplicate_ids(ids, data):
    seen = []
    for key in ("episodes", "characters", "events", "locations",
                "organizations", "objects", "claims", "sources", "evidence"):
        seen += [r["id"] for r in data[key]]
    assert len(seen) == len(set(seen)), "duplicate deterministic id present"


def test_every_claim_has_evidence_and_source(data, ids):
    for c in data["claims"]:
        assert c["evidence_ids"], f"claim without evidence: {c['id']}"
        assert c["source_id"] in ids, f"claim source missing: {c['id']}"
        for ev in c["evidence_ids"]:
            assert ev in ids, f"claim evidence missing: {c['id']}"


def test_every_evidence_references_a_source(data, ids):
    for ev in data["evidence"]:
        assert ev["source_id"] in ids, f"evidence without source: {ev['id']}"


def test_every_ep1_evidence_uses_the_episode_source(data):
    ep1_ev = [e for e in data["evidence"] if e.get("episode_id") == EP]
    assert ep1_ev
    assert all(e["source_id"] == SRC for e in ep1_ev)


def test_all_ep1_story_content_is_visible_from_order_1(data):
    for key in ("characters", "events", "locations", "organizations",
                "objects", "claims", "evidence"):
        for r in data[key]:
            if r.get("episode_id") in (None, EP) and r["id"].split(":")[-1] != "":
                # only assert on records that belong to episode 1 / series-wide
                if r.get("episode_id") == EP or "s01e01" in r["id"] or key in (
                    "organizations", "objects"
                ):
                    assert r["visible_from_order"] == 1, r["id"]


def test_every_ep1_event_has_a_participant(data):
    ep1_events = {e["id"] for e in data["events"] if e.get("episode_id") == EP
                  and "s01e01_" in e["id"]}
    participated = {c["object_id"] for c in data["claims"]
                    if c["predicate"] == "PARTICIPATED_IN"}
    orphans = ep1_events - participated
    assert not orphans, f"events without participant: {sorted(orphans)}"


# ── Spoiler-boundary / unknown-killer safety ──

def test_unknown_killer_stays_unidentified(data):
    itk = "dexter:character:ice_truck_killer"
    rudy = "dexter:character:rudy_cooper"
    node = next(c for c in data["characters"] if c["id"] == itk)
    assert node["visible_from_order"] == 1
    assert "rudy" not in node["label"].lower()
    for c in data["claims"]:
        if itk in (c["subject_id"], c["object_id"]):
            assert rudy not in (c["subject_id"], c["object_id"]), \
                f"unknown killer linked to reveal identity: {c['id']}"
            # never a family / civilian-identity edge
            assert c["predicate"] not in ("FAMILY_OF",), c["id"]


def test_rita_is_not_named_rita_morgan(data):
    rita = next(c for c in data["characters"]
                if c["id"] == "dexter:character:rita_bennett")
    assert rita["label"] == "Rita Bennett"


def test_unidentified_victims_have_no_real_name(data):
    for cid in ("dexter:character:pool_victim",
                "dexter:character:second_bloodless_victim"):
        node = next(c for c in data["characters"] if c["id"] == cid)
        assert "victim" in node["label"].lower()


def test_candidate_victims_marked_candidate(data):
    for cid in ("dexter:character:corey_balanti",
                "dexter:character:tyler_kale",
                "dexter:character:joe_bigalow"):
        node = next(c for c in data["characters"] if c["id"] == cid)
        assert node["origin"] == "candidate"
        assert node.get("confidence_level") == "medium"


def test_interpretive_claims_are_candidate(data):
    for c in data["claims"]:
        if c["claim_type"] == "external_interpretation":
            assert c["origin"] == "candidate", c["id"]
            assert c["status"] == "candidate", c["id"]
            assert c["confidence_level"] in ("low", "medium"), c["id"]


# ── Required characters reused / present ──

@pytest.mark.parametrize("cid", [
    "dexter:character:dexter_morgan", "dexter:character:debra_morgan",
    "dexter:character:angel_batista", "dexter:character:maria_laguerta",
    "dexter:character:james_doakes", "dexter:character:rita_bennett",
])
def test_core_characters_reused(data, cid):
    assert any(c["id"] == cid for c in data["characters"])


@pytest.mark.parametrize("cid", [
    "dexter:character:camilla_figg", "dexter:character:mrs_donovan",
    "dexter:character:jane_saunders", "dexter:character:mike_donovan",
    "dexter:character:jamie_jaworski", "dexter:character:harry_morgan",
])
def test_new_characters_present(data, cid):
    assert any(c["id"] == cid for c in data["characters"])


def test_harry_corrected_to_ep1(data):
    harry = next(c for c in data["characters"]
                 if c["id"] == "dexter:character:harry_morgan")
    assert harry["visible_from_order"] == 1


# ── Required content (claims / nodes) ──

def test_donovan_connects_to_three_victims(data):
    kills = {(c["subject_id"], c["object_id"]) for c in data["claims"]
             if c["predicate"] == "KILLS"
             and c["subject_id"] == "dexter:character:mike_donovan"}
    victims = {v for _, v in kills}
    assert {"dexter:character:corey_balanti",
            "dexter:character:tyler_kale",
            "dexter:character:joe_bigalow"} <= victims


def test_jaworski_linked_to_jane_saunders(data):
    assert any(c["predicate"] == "KILLS"
               and c["subject_id"] == "dexter:character:jamie_jaworski"
               and c["object_id"] == "dexter:character:jane_saunders"
               for c in data["claims"])


def test_seven_seas_pool_location_exists(data):
    assert "Seven Seas Motel Pool" in _node_labels(data, "locations")


def test_baywater_is_the_jaworski_kill_location(data):
    baywater = "dexter:location:baywater"
    kill = next(e for e in data["events"]
                if e["id"] == "dexter:event:s01e01_baywater_kill")
    assert kill["location_id"] == baywater


@pytest.mark.parametrize("needle", [
    "no visible blood",              # pool victim bloodless
    "right leg is divided into four",  # uneven leg segmentation
    "cell crystallization",          # cold-body clue
    "faulty warrant",                # Jaworski escaped justice
    "refrigerated truck",            # truck theory
    "head is missing",               # second victim
    "emotional killing pattern",     # cokehead reconstruction
    "demands",                       # Doakes demands report
    "friendly challenge",            # doll interpretation
    "cell crystallization",
])
def test_required_claims_exist(data, needle):
    assert _has_claim(data, needle), f"missing claim: {needle}"


def test_former_boyfriend_arrest_not_conviction(data):
    labels = " ".join(_claim_labels(data)).lower()
    assert "arrest" in labels and "former boyfriend" in labels
    assert "convicted" not in labels and "conviction of the former" not in labels


def test_doll_head_and_body_objects_exist(data):
    labels = _node_labels(data, "objects")
    assert "Doll Head" in labels
    assert "Dismembered Doll" in labels


def test_debra_theory_presentation_and_rejection(data):
    assert _has_claim(data, "presents the refrigerated-truck theory")
    assert _has_claim(data, "rejects the refrigerated-truck theory")


def test_matthews_assigns_debra_not_permanent_transfer(data):
    assert _has_claim(data, "assigns Debra to the bloodless-body case")
    # do not overstate a permanent Homicide transfer in Episode 1
    assert not _has_claim(data, "permanently transferred to Homicide")


def test_cody_interruption_and_rita_intimacy(data):
    assert _has_claim(data, "Cody becomes sick")
    assert _has_claim(data, "may be ready for intimacy")


def test_severed_head_thrown_at_car(data):
    assert _has_claim(data, "throws the missing victim's severed head at Dexter's car")


def test_episode_metadata_enriched(data):
    ep = next(e for e in data["episodes"] if e["id"] == EP)
    assert ep.get("production_code") == "101"
    assert ep.get("airdate") == "2006-10-01"
    assert ep.get("source_id") == SRC
    assert ep.get("synopsis")


def test_source_points_to_local_snapshot(data):
    src = next(s for s in data["sources"] if s["id"] == SRC)
    assert src.get("local_snapshot_path") == "docs/sources/dexter/episode_101_fandom.txt"
    assert src.get("url") == "https://dexter.fandom.com/wiki/Episode_101:_Dexter"
