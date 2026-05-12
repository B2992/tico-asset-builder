from tico_asset_builder.names import normalized_name, strip_compound_suffix


def test_normalized_name_removes_regions_and_symbols() -> None:
    assert normalized_name("Super Game (USA) [Rev 1]!") == "super game"


def test_strip_compound_suffix() -> None:
    assert strip_compound_suffix("Game.nkit.iso") == "Game"

