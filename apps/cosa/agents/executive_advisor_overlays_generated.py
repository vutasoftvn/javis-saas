# GENERATED FILE — DO NOT MODIFY DIRECTLY
# Source: shared/contracts/executive-advisor-overlays.json · Generator: scripts/gen-executive-advisor-overlays.mjs
# To update: run scripts/sync_executive_advisor_overlays.py then node scripts/gen-executive-advisor-overlays.mjs
from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class PinnedSkillIdentity:
    skill_id: str
    version: str
    definition_hash: str


@dataclass(frozen=True)
class AdvisorOverlayDefinition:
    role_key: str
    overlay_spec_id: str
    overlay_spec_version: str
    overlay_definition_hash: str
    required_profile_key: str
    skill_pins: tuple[PinnedSkillIdentity, ...]
    advisory_only: bool


ADVISOR_OVERLAY_CATALOG: Final[dict[str, AdvisorOverlayDefinition]] = {
    "chief_of_staff": AdvisorOverlayDefinition(
        role_key="chief_of_staff",
        overlay_spec_id="cosa.executive.chief_of_staff",
        overlay_spec_version="1.0.0",
        overlay_definition_hash=(
            "2dca87274c2e61cbe6fb7fab86c512f09d816c071825a86900ac7c9e9d6c704f"
        ),
        required_profile_key="operations",
        skill_pins=(
            PinnedSkillIdentity(
                skill_id="executive.board-protocol",
                version="1.0.0",
                definition_hash=(
                    "e8fdd15bd8010c1d5636c026dd63e03d8ecf2c9165f3cce29ec839f94853ce96"
                ),
            ),
            PinnedSkillIdentity(
                skill_id="executive.chief-of-staff",
                version="1.0.0",
                definition_hash=(
                    "ee99e1b7d9bccab53d0a110abc7919e9628420ed45300196f7170bb0d3ca9a90"
                ),
            ),
        ),
        advisory_only=True,
    ),
    "ceo": AdvisorOverlayDefinition(
        role_key="ceo",
        overlay_spec_id="cosa.executive.ceo",
        overlay_spec_version="1.1.0",
        overlay_definition_hash=(
            "9e49f2ad24bab202d1f46b665052efeccb5902f815a8472faa59314b4336177d"
        ),
        required_profile_key="operations",
        skill_pins=(
            PinnedSkillIdentity(
                skill_id="executive.ceo-advisor",
                version="1.0.0",
                definition_hash=(
                    "7de38afd93f98ffc285792f3ac7e2601feb452cb2af3a13c996c40757280b1a2"
                ),
            ),
        ),
        advisory_only=True,
    ),
    "cto": AdvisorOverlayDefinition(
        role_key="cto",
        overlay_spec_id="cosa.executive.cto",
        overlay_spec_version="1.2.0",
        overlay_definition_hash=(
            "e6c5ae120d9ec335a123de98bf9b01e6c72cb536ca761e138728fe6bdf6ea40a"
        ),
        required_profile_key="coding",
        skill_pins=(
            PinnedSkillIdentity(
                skill_id="executive.cto-advisor",
                version="1.0.0",
                definition_hash=(
                    "021076c53f5be56aa07e1edbdb49afe173b6cd5368f15c4392e3aac4dd742667"
                ),
            ),
            PinnedSkillIdentity(
                skill_id="engineering.workspace-site-builder",
                version="1.0.0",
                definition_hash=(
                    "e593a2256237dd91f35c981326c11936b7ad45df74fbd67a26df171bd36e0fe0"
                ),
            ),
        ),
        advisory_only=True,
    ),
    "cfo": AdvisorOverlayDefinition(
        role_key="cfo",
        overlay_spec_id="cosa.executive.cfo",
        overlay_spec_version="1.0.0",
        overlay_definition_hash=(
            "140e55ec1140a4c0f166e26b9939c6d8f16a67fe4406fd77ee5040d31ec989a4"
        ),
        required_profile_key="finance",
        skill_pins=(
            PinnedSkillIdentity(
                skill_id="executive.cfo-advisor",
                version="1.0.0",
                definition_hash=(
                    "52dbcc7b0dd1c6236c9dff6821739087e4904656d714ff1eb50ea99294bed3da"
                ),
            ),
        ),
        advisory_only=True,
    ),
    "cmo": AdvisorOverlayDefinition(
        role_key="cmo",
        overlay_spec_id="cosa.executive.cmo",
        overlay_spec_version="1.0.0",
        overlay_definition_hash=(
            "09eb626b040fe5aecc8c66a9c7357d2729ea2361a9d306ebe812fdfbdb6149ae"
        ),
        required_profile_key="marketing",
        skill_pins=(
            PinnedSkillIdentity(
                skill_id="executive.cmo-advisor",
                version="1.0.0",
                definition_hash=(
                    "aa042d0f313687c2f225ce5bff34ee8704615ddff55c2dbd7a054afa9aaea24f"
                ),
            ),
        ),
        advisory_only=True,
    ),
    "coo": AdvisorOverlayDefinition(
        role_key="coo",
        overlay_spec_id="cosa.executive.coo",
        overlay_spec_version="1.0.0",
        overlay_definition_hash=(
            "3eabe10f74a545a8f3b3f54c434e2277979ec36dd8ecb3d13791a960b42515a4"
        ),
        required_profile_key="operations",
        skill_pins=(
            PinnedSkillIdentity(
                skill_id="executive.coo-advisor",
                version="1.0.0",
                definition_hash=(
                    "b17c6f6bf6c4931241d0f6a410dd0090531f02c83d6eecae08159f2e8cf870c3"
                ),
            ),
        ),
        advisory_only=True,
    ),
    "cro": AdvisorOverlayDefinition(
        role_key="cro",
        overlay_spec_id="cosa.executive.cro",
        overlay_spec_version="1.1.0",
        overlay_definition_hash=(
            "55b0df2e6bdde7cbb3ad4a86122639514adfb262d06eff4eba9dc7598cbd1f75"
        ),
        required_profile_key="sales",
        skill_pins=(
            PinnedSkillIdentity(
                skill_id="executive.cro-advisor",
                version="1.0.0",
                definition_hash=(
                    "c772513824907d8a61f02dc8af40ca6e34a74f3230126c46e44b36fe68c77db2"
                ),
            ),
        ),
        advisory_only=True,
    ),
    "cpo": AdvisorOverlayDefinition(
        role_key="cpo",
        overlay_spec_id="cosa.executive.cpo",
        overlay_spec_version="1.2.0",
        overlay_definition_hash=(
            "7c342646354d613e27429fbda92f6ba9ebf128e5d29bcb376069b9c96ba59efb"
        ),
        required_profile_key="product",
        skill_pins=(
            PinnedSkillIdentity(
                skill_id="executive.cpo-advisor",
                version="1.0.0",
                definition_hash=(
                    "39973d3d3bd616c8c9653fa2a722ae080d317441406c2e33153ea89c2bed18be"
                ),
            ),
        ),
        advisory_only=True,
    ),
    "cco": AdvisorOverlayDefinition(
        role_key="cco",
        overlay_spec_id="cosa.executive.cco",
        overlay_spec_version="1.0.0",
        overlay_definition_hash=(
            "62159f18496512a9d579340ddc8938ffe8ee6d80711046cb8dcd1fe11af7145a"
        ),
        required_profile_key="customer_support",
        skill_pins=(
            PinnedSkillIdentity(
                skill_id="executive.cco-advisor",
                version="1.0.0",
                definition_hash=(
                    "ef0f9d4ebc726a725dde5260b175acafca529755ac0522ea7967d5fe74a2c1eb"
                ),
            ),
        ),
        advisory_only=True,
    ),
    "chro": AdvisorOverlayDefinition(
        role_key="chro",
        overlay_spec_id="cosa.executive.chro",
        overlay_spec_version="1.1.0",
        overlay_definition_hash=(
            "7c8d6f5bfd4aea9904ceeb38d1139ebb00750e7a9f84c8179e5e64eb17d47c5c"
        ),
        required_profile_key="people",
        skill_pins=(
            PinnedSkillIdentity(
                skill_id="executive.chro-advisor",
                version="1.0.0",
                definition_hash=(
                    "bb5d73d7fc6f7ebe5963417c6d2df3782580be0a3798d1a24e7b88758e8643c8"
                ),
            ),
        ),
        advisory_only=True,
    ),
    "ciso": AdvisorOverlayDefinition(
        role_key="ciso",
        overlay_spec_id="cosa.executive.ciso",
        overlay_spec_version="1.1.0",
        overlay_definition_hash=(
            "e8aa3cd94921fcee6368af9c8fdbf5943761fd10a4299bd5d3fd2f93c22ff8f3"
        ),
        required_profile_key="security",
        skill_pins=(
            PinnedSkillIdentity(
                skill_id="executive.ciso-advisor",
                version="1.0.0",
                definition_hash=(
                    "49a4d6a46ed6b0437b7730b7e091c0fe84691e0d9545b663fbfbe0a7494d7485"
                ),
            ),
        ),
        advisory_only=True,
    ),
    "gc": AdvisorOverlayDefinition(
        role_key="gc",
        overlay_spec_id="cosa.executive.gc",
        overlay_spec_version="1.1.0",
        overlay_definition_hash=(
            "b4f226749311d6be54c9db05e7a08d3427895e25b3f06e3ff0441c5ec6e8f13b"
        ),
        required_profile_key="legal",
        skill_pins=(
            PinnedSkillIdentity(
                skill_id="executive.gc-advisor",
                version="1.0.0",
                definition_hash=(
                    "5cedb3d84ba6263aac8ff948c091416db68d2aebaa82d5ea576984cdd4cabca5"
                ),
            ),
        ),
        advisory_only=True,
    ),
    "cdo": AdvisorOverlayDefinition(
        role_key="cdo",
        overlay_spec_id="cosa.executive.cdo",
        overlay_spec_version="1.1.0",
        overlay_definition_hash=(
            "944f76d4f8780baf1216d12d70adcb8211e877548d4fa936df5d33d0489fb9a8"
        ),
        required_profile_key="data",
        skill_pins=(
            PinnedSkillIdentity(
                skill_id="executive.cdo-advisor",
                version="1.0.0",
                definition_hash=(
                    "98224cb8380143c6a9f2bd60c14620bb040ba9f8b8c1236b0f9518fe49c8ccad"
                ),
            ),
        ),
        advisory_only=True,
    ),
    "caio": AdvisorOverlayDefinition(
        role_key="caio",
        overlay_spec_id="cosa.executive.caio",
        overlay_spec_version="1.1.0",
        overlay_definition_hash=(
            "ad7b4872d29543d6b5cff850d00abcfa2fd6721009cd6c950946fad2c07dd8a3"
        ),
        required_profile_key="ai_governance",
        skill_pins=(
            PinnedSkillIdentity(
                skill_id="executive.caio-advisor",
                version="1.0.0",
                definition_hash=(
                    "7431268b12a450b3158461a770f0cd25b5fa72e038c327fd774e7226344d6bdb"
                ),
            ),
        ),
        advisory_only=True,
    ),
    "vpe": AdvisorOverlayDefinition(
        role_key="vpe",
        overlay_spec_id="cosa.executive.vpe",
        overlay_spec_version="1.1.0",
        overlay_definition_hash=(
            "126fddd5ef7284482aff798910efc82b2105bacfac46947d6cb453685a3844a5"
        ),
        required_profile_key="coding",
        skill_pins=(
            PinnedSkillIdentity(
                skill_id="executive.vpe-advisor",
                version="1.0.0",
                definition_hash=(
                    "865c8411d9c2ec11e67f5f522d6abf046117cc9a590fb56a5bc99d94c3f463cf"
                ),
            ),
        ),
        advisory_only=True,
    ),
}
