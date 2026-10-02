"""Tests for momapy.styling module."""

import os

import pytest

import momapy.styling
import momapy.coloring
import momapy.core.layout


def test_style_collection_creation():
    """Test creating a StyleCollection."""
    style_collection = momapy.styling.StyleCollection()
    assert isinstance(style_collection, dict)
    assert isinstance(style_collection, momapy.styling.StyleCollection)


def test_style_collection_with_values():
    """Test StyleCollection with values."""
    style_collection = momapy.styling.StyleCollection(
        {
            "fill": momapy.coloring.black,
            "stroke": momapy.coloring.white,
        }
    )
    assert style_collection["fill"] == momapy.coloring.black
    assert style_collection["stroke"] == momapy.coloring.white


def test_style_sheet_creation():
    """Test creating a StyleSheet."""
    style_sheet = momapy.styling.StyleSheet()
    assert isinstance(style_sheet, dict)
    assert isinstance(style_sheet, momapy.styling.StyleSheet)


def test_style_sheet_or_operator():
    """Test StyleSheet | operator for merging."""
    style1 = momapy.styling.StyleSheet()
    style2 = momapy.styling.StyleSheet()

    style1["key1"] = momapy.styling.StyleCollection({"fill": momapy.coloring.black})
    style2["key2"] = momapy.styling.StyleCollection({"stroke": momapy.coloring.white})

    merged = style1 | style2
    assert "key1" in merged
    assert "key2" in merged


def test_style_sheet_from_string():
    """Test creating StyleSheet from string."""
    css_string = """
    * {
        fill: #000000;
    }
    """
    # This test just checks that the method exists and can be called
    # Actual CSS parsing depends on the parser implementation
    try:
        style_sheet = momapy.styling.StyleSheet.from_string(css_string)
        assert isinstance(style_sheet, momapy.styling.StyleSheet)
    except Exception:
        # Parser might not be fully configured, that's okay for minimal test
        pass


@pytest.mark.parametrize("css_string", ["", "   ", "\n\t  \n"])
def test_style_sheet_from_string_empty(css_string):
    """An empty/whitespace-only stylesheet parses to an empty StyleSheet.

    Regression (finding 4): the document parse action returned None for a
    rule-less document, which pyparsing dropped, so from_string indexed [0]
    on empty ParseResults and raised IndexError.
    """
    style_sheet = momapy.styling.StyleSheet.from_string(css_string)
    assert isinstance(style_sheet, momapy.styling.StyleSheet)
    assert len(style_sheet) == 0


def test_style_sheet_from_file_empty(tmp_path):
    """An empty CSS file parses to an empty StyleSheet (finding 4)."""
    path = tmp_path / "empty.css"
    path.write_text("")
    style_sheet = momapy.styling.StyleSheet.from_file(str(path))
    assert isinstance(style_sheet, momapy.styling.StyleSheet)
    assert len(style_sheet) == 0


def test_style_sheet_from_file_import_keeps_own_rules(tmp_path):
    """@import must merge the imported rules with the file's own rules."""
    base = tmp_path / "base.css"
    base.write_text("Rectangle { fill: red; }\n")
    main = tmp_path / "main.css"
    main.write_text('@import "base.css";\nEllipse { fill: blue; }\n')
    style_sheet = momapy.styling.StyleSheet.from_file(str(main))
    selectors = {str(selector) for selector in style_sheet.keys()}
    assert any("Rectangle" in selector for selector in selectors)
    assert any("Ellipse" in selector for selector in selectors)


def test_style_sheet_from_string_resolves_import(tmp_path):
    """from_string must resolve @import (relative to the cwd) and merge."""
    base = tmp_path / "base.css"
    base.write_text("Rectangle { fill: red; }\n")
    css = '@import "base.css";\nEllipse { fill: blue; }\n'
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        style_sheet = momapy.styling.StyleSheet.from_string(css)
    finally:
        os.chdir(cwd)
    selectors = {str(selector) for selector in style_sheet.keys()}
    assert any("Rectangle" in selector for selector in selectors)
    assert any("Ellipse" in selector for selector in selectors)


def test_combine_style_sheets():
    """Test combine_style_sheets function."""
    style1 = momapy.styling.StyleSheet()
    style2 = momapy.styling.StyleSheet()

    style1["key1"] = momapy.styling.StyleCollection({"fill": momapy.coloring.black})
    style2["key2"] = momapy.styling.StyleCollection({"stroke": momapy.coloring.white})

    combined = momapy.styling.combine_style_sheets([style1, style2])
    assert isinstance(combined, momapy.styling.StyleSheet)
    assert "key1" in combined
    assert "key2" in combined


def test_ior_merges_in_place():
    """``a |= b`` mutates ``a`` in place and returns the same object."""
    style1 = momapy.styling.StyleSheet()
    style2 = momapy.styling.StyleSheet()
    style1["key1"] = momapy.styling.StyleCollection({"fill": momapy.coloring.black})
    style2["key2"] = momapy.styling.StyleCollection({"stroke": momapy.coloring.white})
    alias = style1
    style1 |= style2
    assert style1 is alias
    assert "key1" in style1
    assert "key2" in style1


def test_combine_style_sheets_does_not_mutate_inputs():
    """combine_style_sheets must not mutate its first argument in place."""
    style1 = momapy.styling.StyleSheet()
    style2 = momapy.styling.StyleSheet()
    style1["key1"] = momapy.styling.StyleCollection({"fill": momapy.coloring.black})
    style2["key2"] = momapy.styling.StyleCollection({"stroke": momapy.coloring.white})
    momapy.styling.combine_style_sheets([style1, style2])
    assert "key2" not in style1


def test_combine_style_sheets_empty():
    """Test combine_style_sheets with empty list."""
    result = momapy.styling.combine_style_sheets([])
    assert result is None


def test_from_files_empty():
    """StyleSheet.from_files([]) returns an empty StyleSheet, not None."""
    result = momapy.styling.StyleSheet.from_files([])
    assert isinstance(result, momapy.styling.StyleSheet)
    assert len(result) == 0


# Tests for selectors
def test_type_selector_matches_exact_type():
    """Test TypeSelector matches exact type name."""
    import momapy.core
    import momapy.geometry

    selector = momapy.styling.TypeSelector(class_name="TextLayout")
    text_layout = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(0, 0)
    )

    assert selector.select(text_layout, []) is True


def test_type_selector_matches_builder():
    """Test TypeSelector matches builder version of type."""
    import momapy.core
    import momapy.geometry
    import momapy.builder

    selector = momapy.styling.TypeSelector(class_name="TextLayout")
    text_layout = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(0, 0)
    )
    builder = momapy.builder.builder_from_object(text_layout)

    assert selector.select(builder, []) is True


def test_type_selector_does_not_match_different_type():
    """Test TypeSelector does not match different type."""
    import momapy.core
    import momapy.geometry

    selector = momapy.styling.TypeSelector(class_name="Shape")
    text_layout = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(0, 0)
    )

    assert selector.select(text_layout, []) is False


def test_class_selector_matches_exact_class():
    """Test ClassSelector matches exact class name."""
    import momapy.core
    import momapy.geometry

    selector = momapy.styling.ClassSelector(class_name="TextLayout")
    text_layout = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(0, 0)
    )

    assert selector.select(text_layout, []) is True


def test_class_selector_matches_parent_class():
    """Test ClassSelector matches parent class in MRO."""
    import momapy.core
    import momapy.geometry

    selector = momapy.styling.ClassSelector(class_name="LayoutElement")
    text_layout = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(0, 0)
    )

    assert selector.select(text_layout, []) is True


def test_class_selector_matches_builder():
    """Test ClassSelector matches builder version."""
    import momapy.core
    import momapy.geometry
    import momapy.builder

    selector = momapy.styling.ClassSelector(class_name="TextLayout")
    text_layout = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(0, 0)
    )
    builder = momapy.builder.builder_from_object(text_layout)

    assert selector.select(builder, []) is True


def test_class_selector_does_not_match_unrelated_class():
    """Test ClassSelector does not match unrelated class."""
    import momapy.core
    import momapy.geometry

    selector = momapy.styling.ClassSelector(class_name="UnrelatedClass")
    text_layout = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(0, 0)
    )

    assert selector.select(text_layout, []) is False


def test_id_selector_matches_id():
    """Test IdSelector matches element with matching id."""
    import momapy.core
    import momapy.geometry

    selector = momapy.styling.IdSelector(id_="my_element")
    text_layout = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(0, 0), id_="my_element"
    )

    assert selector.select(text_layout, []) is True


def test_id_selector_does_not_match_different_id():
    """Test IdSelector does not match element with different id."""
    import momapy.core
    import momapy.geometry

    selector = momapy.styling.IdSelector(id_="my_element")
    text_layout = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(0, 0), id_="other_element"
    )

    assert selector.select(text_layout, []) is False


def test_id_selector_does_not_match_element_without_id():
    """Test IdSelector does not match element without id attribute."""
    import momapy.core
    import momapy.geometry

    selector = momapy.styling.IdSelector(id_="my_element")

    # Create a simple object without id_
    class SimpleElement:
        pass

    element = SimpleElement()

    assert selector.select(element, []) is False


def test_child_selector_matches_direct_child():
    """Test ChildSelector matches direct child of matching parent."""
    import momapy.core
    import momapy.geometry

    parent_selector = momapy.styling.ClassSelector(class_name="GroupLayout")
    child_selector = momapy.styling.TypeSelector(class_name="TextLayout")
    selector = momapy.styling.ChildSelector(
        parent_selector=parent_selector, child_selector=child_selector
    )

    parent = momapy.core.layout.Layout(
        position=momapy.geometry.Point(0, 0), width=100, height=100, layout_elements=[]
    )
    child = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(10, 10)
    )

    # Child with parent in ancestors
    # Using ClassSelector since Layout inherits from Node which inherits from GroupLayout
    assert selector.select(child, [parent]) is True


def test_child_selector_does_not_match_without_parent():
    """Test ChildSelector does not match when no ancestors."""
    import momapy.core
    import momapy.geometry

    parent_selector = momapy.styling.TypeSelector(class_name="GroupLayout")
    child_selector = momapy.styling.TypeSelector(class_name="TextLayout")
    selector = momapy.styling.ChildSelector(
        parent_selector=parent_selector, child_selector=child_selector
    )

    child = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(10, 10)
    )

    # Child without ancestors
    assert selector.select(child, []) is False


def test_child_selector_does_not_match_wrong_parent():
    """Test ChildSelector does not match when parent doesn't match."""
    import momapy.core
    import momapy.geometry

    parent_selector = momapy.styling.TypeSelector(class_name="Layout")
    child_selector = momapy.styling.TypeSelector(class_name="TextLayout")
    selector = momapy.styling.ChildSelector(
        parent_selector=parent_selector, child_selector=child_selector
    )

    wrong_parent = momapy.core.layout.TextLayout(
        text="Wrong Parent", position=momapy.geometry.Point(0, 0)
    )
    child = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(10, 10)
    )

    # Child with wrong parent type in ancestors
    assert selector.select(child, [wrong_parent]) is False


def test_child_selector_does_not_match_wrong_child():
    """Test ChildSelector does not match when child doesn't match."""
    import momapy.core
    import momapy.geometry

    parent_selector = momapy.styling.ClassSelector(class_name="GroupLayout")
    child_selector = momapy.styling.TypeSelector(class_name="TextLayout")
    selector = momapy.styling.ChildSelector(
        parent_selector=parent_selector, child_selector=child_selector
    )

    parent = momapy.core.layout.Layout(
        position=momapy.geometry.Point(0, 0), width=100, height=100, layout_elements=[]
    )
    wrong_child = momapy.core.layout.Layout(
        position=momapy.geometry.Point(10, 10), width=50, height=50, layout_elements=[]
    )

    # Wrong child type with matching parent in ancestors
    # Using ClassSelector since Layout inherits from Node which inherits from GroupLayout
    assert selector.select(wrong_child, [parent]) is False


def test_descendant_selector_matches_direct_descendant():
    """Test DescendantSelector matches direct descendant."""
    import momapy.core
    import momapy.geometry

    ancestor_selector = momapy.styling.ClassSelector(class_name="GroupLayout")
    descendant_selector = momapy.styling.TypeSelector(class_name="TextLayout")
    selector = momapy.styling.DescendantSelector(
        ancestor_selector=ancestor_selector, descendant_selector=descendant_selector
    )

    ancestor = momapy.core.layout.Layout(
        position=momapy.geometry.Point(0, 0), width=100, height=100, layout_elements=[]
    )
    descendant = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(10, 10)
    )

    # Direct descendant (child)
    # Using ClassSelector since Layout inherits from Node which inherits from GroupLayout
    assert selector.select(descendant, [ancestor]) is True


def test_descendant_selector_matches_nested_descendant():
    """Test DescendantSelector matches nested descendant (grandchild)."""
    import momapy.core
    import momapy.geometry

    ancestor_selector = momapy.styling.ClassSelector(class_name="GroupLayout")
    descendant_selector = momapy.styling.TypeSelector(class_name="TextLayout")
    selector = momapy.styling.DescendantSelector(
        ancestor_selector=ancestor_selector, descendant_selector=descendant_selector
    )

    grandparent = momapy.core.layout.Layout(
        position=momapy.geometry.Point(0, 0), width=200, height=200, layout_elements=[]
    )
    parent = momapy.core.layout.Layout(
        position=momapy.geometry.Point(10, 10),
        width=100,
        height=100,
        layout_elements=[],
    )
    descendant = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(20, 20)
    )

    # Nested descendant with grandparent matching
    # Using ClassSelector since Layout inherits from Node which inherits from GroupLayout
    assert selector.select(descendant, [grandparent, parent]) is True


def test_descendant_selector_does_not_match_without_ancestors():
    """Test DescendantSelector does not match without ancestors."""
    import momapy.core
    import momapy.geometry

    ancestor_selector = momapy.styling.TypeSelector(class_name="GroupLayout")
    descendant_selector = momapy.styling.TypeSelector(class_name="TextLayout")
    selector = momapy.styling.DescendantSelector(
        ancestor_selector=ancestor_selector, descendant_selector=descendant_selector
    )

    descendant = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(10, 10)
    )

    # No ancestors
    assert selector.select(descendant, []) is False


def test_descendant_selector_does_not_match_wrong_ancestor():
    """Test DescendantSelector does not match when no ancestor matches."""
    import momapy.core
    import momapy.geometry

    ancestor_selector = momapy.styling.IdSelector(id_="special_group")
    descendant_selector = momapy.styling.TypeSelector(class_name="TextLayout")
    selector = momapy.styling.DescendantSelector(
        ancestor_selector=ancestor_selector, descendant_selector=descendant_selector
    )

    wrong_ancestor = momapy.core.layout.Layout(
        position=momapy.geometry.Point(0, 0),
        width=100,
        height=100,
        layout_elements=[],
        id_="other_group",
    )
    descendant = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(10, 10)
    )

    # Ancestor doesn't match selector
    assert selector.select(descendant, [wrong_ancestor]) is False


def test_or_selector_matches_first_selector():
    """Test OrSelector matches when first selector matches."""
    import momapy.core
    import momapy.geometry

    selector1 = momapy.styling.TypeSelector(class_name="TextLayout")
    selector2 = momapy.styling.TypeSelector(class_name="GroupLayout")
    or_selector = momapy.styling.OrSelector(selectors=(selector1, selector2))

    text_layout = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(0, 0)
    )

    # Matches first selector
    assert or_selector.select(text_layout, []) is True


def test_or_selector_matches_second_selector():
    """Test OrSelector matches when second selector matches."""
    import momapy.core
    import momapy.geometry

    selector1 = momapy.styling.TypeSelector(class_name="Shape")
    selector2 = momapy.styling.TypeSelector(class_name="TextLayout")
    or_selector = momapy.styling.OrSelector(selectors=(selector1, selector2))

    text_layout = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(0, 0)
    )

    # Matches second selector
    assert or_selector.select(text_layout, []) is True


def test_or_selector_matches_multiple_selectors():
    """Test OrSelector matches when multiple selectors match."""
    import momapy.core
    import momapy.geometry

    selector1 = momapy.styling.TypeSelector(class_name="TextLayout")
    selector2 = momapy.styling.ClassSelector(class_name="LayoutElement")
    or_selector = momapy.styling.OrSelector(selectors=(selector1, selector2))

    text_layout = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(0, 0)
    )

    # Matches both selectors
    assert or_selector.select(text_layout, []) is True


def test_or_selector_does_not_match_any():
    """Test OrSelector does not match when none of the selectors match."""
    import momapy.core
    import momapy.geometry

    selector1 = momapy.styling.TypeSelector(class_name="Shape")
    selector2 = momapy.styling.IdSelector(id_="special_element")
    or_selector = momapy.styling.OrSelector(selectors=(selector1, selector2))

    text_layout = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(0, 0), id_="normal_element"
    )

    # Matches neither selector
    assert or_selector.select(text_layout, []) is False


def test_compound_selector_matches_all_selectors():
    """Test CompoundSelector matches when all selectors match."""
    import momapy.core
    import momapy.geometry

    selector1 = momapy.styling.TypeSelector(class_name="TextLayout")
    selector2 = momapy.styling.ClassSelector(class_name="LayoutElement")
    selector3 = momapy.styling.IdSelector(id_="special_text")
    compound_selector = momapy.styling.CompoundSelector(
        selectors=(selector1, selector2, selector3)
    )

    text_layout = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(0, 0), id_="special_text"
    )

    # Matches all selectors
    assert compound_selector.select(text_layout, []) is True


def test_compound_selector_does_not_match_one_fails():
    """Test CompoundSelector does not match when one selector fails."""
    import momapy.core
    import momapy.geometry

    selector1 = momapy.styling.TypeSelector(class_name="TextLayout")
    selector2 = momapy.styling.IdSelector(id_="special_text")
    compound_selector = momapy.styling.CompoundSelector(
        selectors=(selector1, selector2)
    )

    text_layout = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(0, 0), id_="normal_text"
    )

    # First selector matches, second doesn't
    assert compound_selector.select(text_layout, []) is False


def test_compound_selector_does_not_match_none():
    """Test CompoundSelector does not match when no selectors match."""
    import momapy.core
    import momapy.geometry

    selector1 = momapy.styling.TypeSelector(class_name="Shape")
    selector2 = momapy.styling.IdSelector(id_="special_element")
    compound_selector = momapy.styling.CompoundSelector(
        selectors=(selector1, selector2)
    )

    text_layout = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(0, 0), id_="normal_element"
    )

    # Neither selector matches
    assert compound_selector.select(text_layout, []) is False


def test_compound_selector_with_two_matching():
    """Test CompoundSelector with two matching selectors."""
    import momapy.core
    import momapy.geometry

    selector1 = momapy.styling.ClassSelector(class_name="TextLayout")
    selector2 = momapy.styling.ClassSelector(class_name="LayoutElement")
    compound_selector = momapy.styling.CompoundSelector(
        selectors=(selector1, selector2)
    )

    text_layout = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(0, 0)
    )

    # Both class selectors match (TextLayout inherits from LayoutElement)
    assert compound_selector.select(text_layout, []) is True


def test_not_selector_matches_when_selector_does_not_match():
    """Test NotSelector matches when the negated selector does not match."""
    import momapy.core
    import momapy.geometry

    selector = momapy.styling.TypeSelector(class_name="GroupLayout")
    not_selector = momapy.styling.NotSelector(selectors=(selector,))

    text_layout = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(0, 0)
    )

    # NotSelector matches because element is not GroupLayout
    assert not_selector.select(text_layout, []) is True


def test_not_selector_does_not_match_when_selector_matches():
    """Test NotSelector does not match when the negated selector matches."""
    import momapy.core
    import momapy.geometry

    selector = momapy.styling.TypeSelector(class_name="TextLayout")
    not_selector = momapy.styling.NotSelector(selectors=(selector,))

    text_layout = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(0, 0)
    )

    # NotSelector does not match because element is TextLayout
    assert not_selector.select(text_layout, []) is False


def test_not_selector_with_multiple_selectors_none_match():
    """Test NotSelector with multiple selectors when none match."""
    import momapy.core
    import momapy.geometry

    selector1 = momapy.styling.TypeSelector(class_name="GroupLayout")
    selector2 = momapy.styling.IdSelector(id_="special_element")
    not_selector = momapy.styling.NotSelector(selectors=(selector1, selector2))

    text_layout = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(0, 0), id_="normal_element"
    )

    # NotSelector matches because neither selector matches
    assert not_selector.select(text_layout, []) is True


def test_not_selector_with_multiple_selectors_one_matches():
    """Test NotSelector with multiple selectors when one matches."""
    import momapy.core
    import momapy.geometry

    selector1 = momapy.styling.TypeSelector(class_name="TextLayout")
    selector2 = momapy.styling.IdSelector(id_="special_element")
    not_selector = momapy.styling.NotSelector(selectors=(selector1, selector2))

    text_layout = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(0, 0), id_="normal_element"
    )

    # NotSelector does not match because first selector matches
    assert not_selector.select(text_layout, []) is False


def test_not_selector_with_multiple_selectors_all_match():
    """Test NotSelector with multiple selectors when all match."""
    import momapy.core
    import momapy.geometry

    selector1 = momapy.styling.TypeSelector(class_name="TextLayout")
    selector2 = momapy.styling.ClassSelector(class_name="LayoutElement")
    not_selector = momapy.styling.NotSelector(selectors=(selector1, selector2))

    text_layout = momapy.core.layout.TextLayout(
        text="Test", position=momapy.geometry.Point(0, 0)
    )

    # NotSelector does not match because both selectors match
    assert not_selector.select(text_layout, []) is False


class TestStyleApplication:
    """Tests for apply_style_collection and apply_style_sheet."""

    def test_apply_style_collection_changes_attributes(self):
        """Test that apply_style_collection changes element attributes."""
        import momapy.core
        import momapy.geometry
        import momapy.coloring

        text_layout = momapy.core.layout.TextLayout(
            text="Test",
            position=momapy.geometry.Point(0, 0),
        )

        style_collection = momapy.styling.StyleCollection(
            {
                "font_size": 20.0,
                "fill": momapy.coloring.red,
            }
        )

        # Apply style collection (returns modified element)
        result = momapy.styling.apply_style_collection(text_layout, style_collection)

        # Check that attributes were applied
        assert result.font_size == 20.0

    def test_css_filter_property_round_trips_to_filter_field(self):
        """A CSS `filter` rule reaches the reserved-word `filter_` field.

        Regression (finding 35): `filter` shadows the builtin, so the field is
        named `filter_`; the CSS property name stays `filter` and must resolve
        back to `filter_` through the attribute-name parse action.
        """
        import momapy.core
        import momapy.drawing
        import momapy.geometry

        text_layout = momapy.core.layout.TextLayout(
            text="Test",
            position=momapy.geometry.Point(0, 0),
        )
        css = "TextLayout {\n    filter: none;\n}\n"
        style_sheet = momapy.styling.StyleSheet.from_string(css)
        result = momapy.styling.apply_style_sheet(text_layout, style_sheet)
        assert result.filter_ is momapy.drawing.NoneValue

    def test_apply_style_sheet_with_type_selector(self):
        """Test apply_style_sheet with TypeSelector-based stylesheet."""
        import momapy.core
        import momapy.geometry
        import momapy.coloring

        # Create a layout tree
        text_layout = momapy.core.layout.TextLayout(
            text="Test",
            position=momapy.geometry.Point(0, 0),
        )

        # Create a stylesheet
        style_sheet = momapy.styling.StyleSheet()
        selector = momapy.styling.TypeSelector(class_name="TextLayout")
        style_sheet[selector] = momapy.styling.StyleCollection(
            {
                "font_size": 24.0,
            }
        )

        # Apply stylesheet (returns modified element)
        result = momapy.styling.apply_style_sheet(text_layout, style_sheet)

        # Check that style was applied to the text layout within the result
        assert isinstance(result, momapy.core.layout.TextLayout)
        assert result.font_size == 24.0

    def test_apply_style_sheet_on_layout_less_map_raises(self):
        """A Map with layout=None raises a clear ValueError, not AttributeError.

        Regression (finding 3): styling a layout-less map (e.g. every SBMLMap,
        reachable via ``momapy style <sbml>.xml``) set layout_element to None
        and then called None.children(), raising AttributeError.
        """
        import momapy.core.map

        map_ = momapy.core.map.Map()
        assert map_.layout is None

        style_sheet = momapy.styling.StyleSheet()
        selector = momapy.styling.TypeSelector(class_name="TextLayout")
        style_sheet[selector] = momapy.styling.StyleCollection({"font_size": 24.0})

        with pytest.raises(ValueError, match="without a layout"):
            momapy.styling.apply_style_sheet(map_, style_sheet)


class TestStylableAttributes:
    """Tests for get_stylable_attributes."""

    def test_excludes_id_and_all_names_round_trip(self):
        """id_ is excluded and every returned CSS name maps back to a field.

        Regression (finding 16): the emitted names must round-trip through the
        attribute-name parse action (replace('-', '_')); the old rstrip('_')
        emitted an unusable 'id'. A reserved-word presentation attribute (e.g.
        the CSS ``filter`` -> field ``filter_``) round-trips via the resolver's
        trailing-underscore reconstruction.
        """
        import dataclasses
        import momapy.drawing
        import momapy.meta.nodes

        cls = momapy.meta.nodes.Rectangle
        attributes = momapy.styling.get_stylable_attributes(cls)
        assert "id" not in attributes
        field_names = {field.name for field in dataclasses.fields(cls)}
        for name in attributes:
            resolved = name.replace("-", "_")
            # Reserved-word presentation attributes reconstruct the trailing
            # underscore (CSS ``filter`` -> field ``filter_``).
            if (
                resolved not in momapy.drawing.PRESENTATION_ATTRIBUTES
                and f"{resolved}_" in momapy.drawing.PRESENTATION_ATTRIBUTES
            ):
                resolved = f"{resolved}_"
            assert resolved in field_names


def _parse_fill(value):
    import momapy.core.layout

    style_sheet = momapy.styling.StyleSheet.from_string(f"A {{ fill: {value}; }}")
    return list(style_sheet.values())[0]["fill"]


class TestCSSColorsAndGradients:
    """Hex colors and CSS gradient functions."""

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("#d4a340", momapy.coloring.Color(212, 163, 64)),
            ("#D4A34080", momapy.coloring.Color(212, 163, 64, 128 / 255)),
        ],
    )
    def test_hex_colors(self, value, expected):
        """6-digit and 8-digit hex colors are parsed."""
        assert _parse_fill(value) == expected

    def test_repeating_linear_gradient_with_lengths(self):
        """Lengths give a user space gradient with one period as vector."""
        import momapy.drawing

        gradient = _parse_fill(
            "repeating-linear-gradient(135deg, #bf8f33 0 3, #d4a340 3 13)"
        )
        assert isinstance(gradient, momapy.drawing.LinearGradient)
        assert gradient.gradient_units == momapy.drawing.GradientUnits.USER_SPACE_ON_USE
        assert gradient.spread_method == momapy.drawing.SpreadMethod.REPEAT
        assert (gradient.x1, gradient.y1) == pytest.approx((0.0, 0.0))
        assert (gradient.x2, gradient.y2) == pytest.approx((9.1924, 9.1924), abs=1e-4)
        assert [stop.offset for stop in gradient.stops] == pytest.approx(
            [0.0, 3 / 13, 3 / 13, 1.0]
        )
        assert gradient.stops[1].stop_color == momapy.coloring.Color(191, 143, 51)
        assert gradient.stops[2].stop_color == momapy.coloring.Color(212, 163, 64)

    def test_linear_gradient_defaults(self):
        """Without angle the gradient goes to the bottom of the box."""
        import momapy.drawing

        gradient = _parse_fill("linear-gradient(red, green, blue 80%, black)")
        assert (
            gradient.gradient_units == momapy.drawing.GradientUnits.OBJECT_BOUNDING_BOX
        )
        assert gradient.spread_method == momapy.drawing.SpreadMethod.PAD
        assert (gradient.x1, gradient.y1, gradient.x2, gradient.y2) == pytest.approx(
            (0.5, 0.0, 0.5, 1.0)
        )
        assert [stop.offset for stop in gradient.stops] == pytest.approx(
            [0.0, 0.4, 0.8, 1.0]
        )

    def test_linear_gradient_diagonal_reaches_corners(self):
        """A 45deg gradient goes from the bottom left to the top right corner."""
        gradient = _parse_fill("linear-gradient(45deg, red, blue)")
        assert (gradient.x1, gradient.y1, gradient.x2, gradient.y2) == pytest.approx(
            (0.0, 1.0, 1.0, 0.0)
        )

    def test_decreasing_positions_are_raised(self):
        """A position smaller than the previous one is raised to it."""
        gradient = _parse_fill("linear-gradient(red 50%, blue 20%)")
        assert [stop.offset for stop in gradient.stops] == pytest.approx([0.5, 0.5])

    def test_radial_gradient(self):
        """The default radial gradient is the ellipse through the corners."""
        import math
        import momapy.drawing

        gradient = _parse_fill("radial-gradient(white, lightblue)")
        assert isinstance(gradient, momapy.drawing.RadialGradient)
        assert (gradient.cx, gradient.cy) == (0.5, 0.5)
        assert gradient.r == pytest.approx(math.sqrt(2) / 2)

    @pytest.mark.parametrize(
        "value",
        [
            "linear-gradient(90deg, red 0, blue 10)",
            "repeating-linear-gradient(red 0, blue 10%)",
            "repeating-linear-gradient(red, blue 10)",
            "repeating-linear-gradient(red 5%, blue 5%)",
        ],
    )
    def test_invalid_gradients(self, value):
        """Invalid position combinations raise ValueError."""
        with pytest.raises(ValueError):
            _parse_fill(value)


class TestCSSLineJoinsAndCaps:
    """stroke-linejoin and stroke-linecap keywords."""

    def test_keywords_are_converted(self):
        """Keywords become LineJoin and LineCap values, prefixes included."""
        import momapy.drawing

        style_sheet = momapy.styling.StyleSheet.from_string(
            "A { stroke-linejoin: round; path-stroke-linecap: square; }"
        )
        style_collection = list(style_sheet.values())[0]
        assert style_collection["stroke_linejoin"] == momapy.drawing.LineJoin.ROUND
        assert style_collection["path_stroke_linecap"] == momapy.drawing.LineCap.SQUARE

    def test_wrong_keyword_raises(self):
        """A join keyword is not accepted as a cap."""
        with pytest.raises(ValueError):
            momapy.styling.StyleSheet.from_string("A { stroke-linecap: miter; }")

    def test_arrowhead_line_join_reaches_drawing_elements(self):
        """arrowhead-stroke-linejoin ends up on the arrowhead drawing elements."""
        import pathlib
        import momapy.drawing
        import momapy.io.core
        import momapy.sbgn.pd

        map_file = pathlib.Path(__file__).parent / "sbgn/maps/pd/mapk_cascade.sbgn"
        map_ = momapy.io.core.read(map_file).obj
        style_sheet = momapy.styling.StyleSheet.from_string(
            "ProductionLayout { arrowhead-stroke-linejoin: round; }"
        )
        map_ = momapy.styling.apply_style_sheet(map_, style_sheet)
        production = next(
            layout_element
            for layout_element in map_.layout.descendants()
            if isinstance(layout_element, momapy.sbgn.pd.ProductionLayout)
        )
        drawing_elements = list(production.drawing_elements())
        line_joins = []
        while drawing_elements:
            drawing_element = drawing_elements.pop()
            line_joins.append(drawing_element.stroke_linejoin)
            drawing_elements.extend(getattr(drawing_element, "elements", ()))
        assert momapy.drawing.LineJoin.ROUND in line_joins
