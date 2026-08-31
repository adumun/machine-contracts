from __future__ import annotations

from tools.coi_coverage import build_portfolio_coverage


def main() -> int:
    headers = [
        "ID", "Initiative", "Explore Ideas Folder", "Lifecycle Stage", "Current Gate", "Gate Outcome",
        "Evidence Confidence", "Last Reviewed", "Initiative Lifecycle Folder", "Next Review / Evidence Needed",
        "Notes", "Canonical Lifecycle State", "Reconciliation Status", "Portfolio Object Type", "Authority State",
        "Schema Version", "Normalized Object ID",
    ]
    source = {
        "source_ref": "REG-INIT-LIFECYCLE-001 / Registry",
        "freshness": {"state": "CURRENT", "as_of": "2026-08-30"},
        "confidentiality": {"classification": "INTERNAL"},
        "reconciliation_state": "CURRENT",
        "rows": [
            headers,
            ["1", "Corporate Operating Intelligence", "", "S10 — Operation, Support, Maintenance & Warranty", "G10", "OPEN", "HIGH", "2026-08-30", "", "", "", "OPERATING", "MAPPED", "INITIATIVE", "CURRENT", "initiative-lifecycle-registry.v1.0.0", "INIT-ACC-001"],
            ["2", "Powerful Brain", "", "S8 — Delivery & Continuous Validation", "G8", "OPEN", "HIGH", "2026-08-30", "", "", "", "DELIVERING", "MAPPED", "INITIATIVE", "CURRENT", "initiative-lifecycle-registry.v1.0.0", "INIT-PB-001"],
            ["3", "Project Pulse", "", "", "", "", "MEDIUM", "2026-08-29", "", "Track only as embedded Work OS surface", "Absorbed into Powerful Brain", "", "MAPPED", "APPLICATION_COMPONENT", "CURRENT", "initiative-lifecycle-registry.v1.0.0", "powerful-brain/project-pulse"],
        ],
    }

    portfolio = build_portfolio_coverage(source)
    ids = [item["object_id"] for item in portfolio["comparable_initiatives"]]

    if portfolio["status"] != "AVAILABLE":
        print(f"ERROR expected AVAILABLE initiative coverage, got {portfolio['status']}")
        return 1
    if not portfolio["global_comparison_supported"]:
        print("ERROR governed APPLICATION_COMPONENT must not disable initiative comparison")
        return 1
    if portfolio["non_comparable_row_count"] != 0:
        print("ERROR Project Pulse was incorrectly counted as a non-comparable initiative row")
        return 1
    if portfolio["excluded_non_initiative_row_count"] != 1:
        print("ERROR governed non-initiative exclusion count was not preserved")
        return 1
    if "powerful-brain/project-pulse" in ids:
        print("ERROR Project Pulse leaked into the initiative lifecycle population")
        return 1
    if set(ids) != {"INIT-ACC-001", "INIT-PB-001"}:
        print(f"ERROR unexpected comparable initiative population: {ids}")
        return 1
    if "PORTFOLIO_POPULATION_NOT_FULLY_COMPARABLE" in portfolio["limitations"]:
        print("ERROR a governed non-initiative component produced a false population limitation")
        return 1

    unresolved = {**source, "rows": list(source["rows"]) + [["4", "Unknown candidate", "", "", "", "", "LOW", "2026-08-30", "", "", "", "", "RECONCILIATION_REQUIRED", "UNRESOLVED", "CURRENT", "initiative-lifecycle-registry.v1.0.0", ""]]}
    unresolved_portfolio = build_portfolio_coverage(unresolved)
    if unresolved_portfolio["global_comparison_supported"]:
        print("ERROR unresolved identity must still fail closed")
        return 1
    if unresolved_portfolio["non_comparable_row_count"] != 1:
        print("ERROR unresolved identity was incorrectly excluded")
        return 1

    print("PASS: DEC-ADM-010 semantics keep Project Pulse outside initiative lifecycle comparison")
    print("PASS: governed CURRENT/MAPPED non-initiative components are explicitly excluded, not treated as drift")
    print("PASS: unresolved/stale/unmapped identity remains fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
