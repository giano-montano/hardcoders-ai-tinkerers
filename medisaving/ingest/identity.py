"""Versioned, source-scoped search identities, not clinical interchangeability.

Evidence and exclusions: docs/teams/ingesta-identidad.md.
"""

PROFILE = "opm-identity-v1"
ESCITALOPRAM_RULE = "opm-1515-3-20mg-escitalopram-v1"


def resolve(row, source_substance):
    """Only the observed OPM 20 mg coated-tablet group has been verified."""
    if row.get("identity_rule") not in (None, ESCITALOPRAM_RULE):
        raise ValueError("Unsupported identity rule")
    if (
        str(row.get("source_group")) == "1515"
        and str(row.get("source_form_group")) == "3"
        and row["strength"] == "20mg"
        and row["form"] in {"tableta recubierta", "comprimido recubierto"}
        and source_substance in {"escitalopram", "escitalopram oxalato"}
        and row["medicine_key"] in {source_substance, "escitalopram"}
    ):
        row.update(medicine_key="escitalopram", identity_rule=ESCITALOPRAM_RULE)
    else:
        # Do not retain evidence from an imported row that no longer matches.
        if row.get("identity_rule") is not None:
            raise ValueError("Identity rule does not match source evidence")
    return row
