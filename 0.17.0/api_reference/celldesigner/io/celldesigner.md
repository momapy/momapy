# ID assignment

When reading a CellDesigner file, ID assignment is more complex than SBGN-ML: model and layout often use different XML ID sources (e.g., `<species id>` for the model vs. `<speciesAlias id>` for the layout). Some elements have no XML ID and rely on SBML `metaid`, composite IDs, or auto-generated UUIDs.

**ID provenance key**:

- `sbml:X` — from an SBML element attribute (e.g., `<species id="s1">`, `<modifierSpeciesReference metaid="MSR0">`)
- `cd:X` — from a CellDesigner extension element attribute (e.g., `<speciesAlias id="sa1">`)
- `composite` — synthetic ID built from parent + child XML IDs
- `auto` — auto-generated UUID from the builder

| Element type | Model `id_` | Source | Layout `id_` | Source | Registered | Notes |
|---|---|---|---|---|---|---|
| Compartment | `compartment_id` | sbml:`compartment/@id` | `alias_id` | cd:`compartmentAlias/@id` | yes | `metaid` also stored |
| Species Template | `template_id` | cd:`proteinReference/@id` etc. | no layout | — | yes | |
| Species | `species_id` or `f"{species_id}_active"` | sbml:`species/@id` | `alias_id` | cd:`speciesAlias/@id` | yes | Dual model registration; active species get `_active` suffix |
| ModificationResidue | `f"{template_id}_{residue_id}"` | composite | no layout | — | yes | Global uniqueness via parent |
| Region | `f"{template_id}_{region_id}"` | composite | no layout | — | yes | Global uniqueness via parent |
| Modification | `f"{species_id}_{residue_id}"` | composite | `f"{species_id}_{residue_id}_layout"` | composite | no | Deterministic from species + residue |
| StructuralState | `f"{species_id}_{value}"` | composite | `f"{species_id}_{value}_layout"` | composite | no | Deterministic from species + value; with no value, `structural_state` replaces the value |
| Reactant (base/link) | `metaid` or `f"{reaction_id}_{species_id}"` | sbml:`speciesReference/@metaid` or composite | `f"{model_id}_layout"` | derived from model id | yes | `metaid` preferred; layout only for link reactants and some base |
| Product (base/link) | `metaid` or `f"{reaction_id}_{species_id}"` | sbml:`speciesReference/@metaid` or composite | `f"{model_id}_layout"` | derived from model id | yes | `metaid` preferred; layout only for link products and some base |
| Modulator | `metaid` | sbml:`modifierSpeciesReference/@metaid` | `f"{metaid}_layout"` | derived from metaid | yes | `metaid` always present |
| BooleanGate | `f"{reaction_id}_gate_{sorted_aliases}"` | composite | `f"{...}_layout"` | composite | model only | Deterministic from reaction + sorted aliases |
| BooleanGateInput / LogicArcLayout | `f"{gate_id}_input_{input_alias}"` | composite | `f"{gate_id}_arc_{input_alias}"` | composite | no | Frozen child of gate |
| Reaction | `reaction_id` | sbml:`reaction/@id` | `f"{reaction_id}_layout"` | derived from sbml | yes | No reaction alias in CellDesigner |
| Modulation | `reaction_id` | sbml:`reaction/@id` | `f"{reaction_id}_layout"` | derived from sbml | yes | Encoded as fake reactions |

**Notes**:

- **Dual registration**: Species model is registered in `xml_id_to_model_element` under both `species_id` and `species_alias_id` (CellDesigner reactions reference species by alias ID for cross-reference resolution).
- **`_layout` suffix**: Used when model and layout share the same XML ID source (reactions, modulations, modulators with `metaid`). No suffix is needed when they come from different XML elements (species vs. alias, compartment vs. alias).
- **`metaid`**: The SBML `metaid` attribute is preferred for Reactants, Products, and Modulators. Falls back to a composite ID or UUID when absent.
- **Composite IDs**: `f"{parent_id}_{child_id}"` for ModificationResidue and Region, since child IDs are only unique within a parent template.

# API

::: momapy.celldesigner.io.celldesigner
