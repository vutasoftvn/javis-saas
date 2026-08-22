from agentos.skills.supply_chain.catalog import CatalogSource, ExternalSkillCandidate, StaticCatalogSource


def test_static_catalog_source_satisfies_protocol():
    assert isinstance(StaticCatalogSource([]), CatalogSource)


def test_static_catalog_source_lists_candidates():
    candidate = ExternalSkillCandidate(
        id="community.faq-writer",
        name="FAQ Writer",
        description="Writes FAQ sections",
        repository="https://github.com/example/skills",
        path="skills/faq-writer",
        commit="4bc9a82c1234567890abcdef1234567890abcdef",
    )
    source = StaticCatalogSource([candidate])

    candidates = source.list_candidates()

    assert candidates == [candidate]


def test_static_catalog_source_returns_a_copy_not_the_internal_list():
    source = StaticCatalogSource([])
    result = source.list_candidates()
    result.append(
        ExternalSkillCandidate(id="x", name="x", description="x", repository="x", path="x")
    )

    assert source.list_candidates() == []
