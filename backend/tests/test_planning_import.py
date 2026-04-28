from app.models.planning import PlanningMarkerKind
from app.services.planning_import import normalize_name, split_code


def test_normalize_name_matches_excel_umlauts_to_seed_names():
    assert normalize_name("André Stöcklein") == normalize_name("Andre Stoecklein")


def test_split_composite_code_into_structured_tokens():
    tokens = split_code("BHT")
    assert [token.code for token in tokens] == ["B", "H", "T"]


def test_split_dienstreise_variants():
    assert split_code("dr")[0].code == "DR"
    assert split_code("DR")[0].is_travel is True


def test_split_school_code_is_information_marker():
    token = split_code("S")[0]
    assert token.label == "Schule Azubi"
    assert token.kind == PlanningMarkerKind.INFO
    assert token.absence_type is None
