# ID assignment

When reading an SBGN-ML file, every element follows a consistent pattern:

- Model `id_` = `f"{xml_id}_model"`
- Layout `id_` = `xml_id`

Both `xml_id_to_model_element` and `xml_id_to_layout_element` are keyed by the raw `xml_id`.

| Element type | Model `id_` | Layout `id_` | Registered | Notes |
|---|---|---|---|---|
| Compartment | `f"{glyph_id}_model"` | `glyph_id` | yes | |
| EntityPool / Subunit | `f"{glyph_id}_model"` | `glyph_id` | yes | |
| Activity | `f"{glyph_id}_model"` | `glyph_id` | yes | |
| StateVariable | `f"{glyph_id}_model"` | `glyph_id` | yes | Frozen child |
| UnitOfInformation | `f"{glyph_id}_model"` | `glyph_id` | yes | Frozen child |
| Submap | `f"{glyph_id}_model"` | `glyph_id` | yes | |
| Terminal / Tag | `f"{glyph_id}_model"` | `glyph_id` | yes | |
| TerminalRef / TagRef | `f"{arc_id}_model"` | `arc_id` | yes | Frozen child |
| StoichiometricProcess | `f"{glyph_id}_model"` | `glyph_id` | yes | |
| Reactant | `f"{arc_id}_model"` | `arc_id` | yes | Frozen child |
| Product | `f"{arc_id}_model"` | `arc_id` | yes | Frozen child |
| LogicalOperator | `f"{glyph_id}_model"` | `glyph_id` | yes | |
| LogicalOperatorInput | `f"{arc_id}_model"` | `arc_id` | yes | Frozen child |
| Modulation | `f"{arc_id}_model"` | `arc_id` | yes | |
| Phenotype | `f"{glyph_id}_model"` | `glyph_id` | yes | In `model.processes` |

Map, model, and layout IDs come from `<map id="...">`:

- `map_.id_` = `map_id`
- `model.id_` = `f"{map_id}_model"`
- `layout.id_` = `f"{map_id}_layout"`

These are only set for SBGN-ML 0.3. SBGN-ML 0.2 has no map id, so the builder falls back to UUID defaults.

# API

::: momapy.sbgn.io.sbgnml
