"""Tests for momapy.utils module."""

import pytest
import frozendict
import momapy.utils


class TestSurjectionDict:
    """Tests for SurjectionDict class."""

    def test_init_empty(self):
        """Test creating an empty SurjectionDict."""
        d = momapy.utils.SurjectionDict()
        assert len(d) == 0
        assert len(d.inverse) == 0

    def test_init_with_items(self):
        """Test creating SurjectionDict with initial items."""
        d = momapy.utils.SurjectionDict({"a": 1, "b": 2, "c": 1})
        assert d["a"] == 1
        assert d["b"] == 2
        assert d["c"] == 1
        assert 1 in d.inverse
        assert set(d.inverse[1]) == {"a", "c"}

    def test_setitem(self):
        """Test setting items."""
        d = momapy.utils.SurjectionDict()
        d["key1"] = "value1"
        assert d["key1"] == "value1"
        assert "value1" in d.inverse

    def test_delitem(self):
        """Test deleting items."""
        d = momapy.utils.SurjectionDict({"a": 1, "b": 2})
        del d["a"]
        assert "a" not in d
        assert 1 not in d.inverse

    def test_inverse_property(self):
        """Test inverse property."""
        d = momapy.utils.SurjectionDict({"a": 1, "b": 1, "c": 2})
        inverse = d.inverse
        assert 1 in inverse
        assert set(inverse[1]) == {"a", "b"}
        assert set(inverse[2]) == {"c"}


class TestFrozenSurjectionDict:
    """Tests for FrozenSurjectionDict class."""

    def test_init_empty(self):
        """Test creating an empty FrozenSurjectionDict."""
        d = momapy.utils.FrozenSurjectionDict()
        assert len(d) == 0
        assert len(d.inverse) == 0

    def test_init_with_items(self):
        """Test creating FrozenSurjectionDict with items."""
        d = momapy.utils.FrozenSurjectionDict({"a": 1, "b": 2, "c": 1})
        assert d["a"] == 1
        assert d["b"] == 2
        assert set(d.inverse[1]) == {"a", "c"}

    def test_immutable(self):
        """Test that FrozenSurjectionDict is immutable."""
        d = momapy.utils.FrozenSurjectionDict({"a": 1})
        with pytest.raises(Exception):  # frozendict raises TypeError or similar
            d["b"] = 2


class _Holder:
    """Hashable, ``==``-equal but id-distinct helper for identity tests."""

    def __init__(self, label):
        self.label = label

    def __eq__(self, other):
        return isinstance(other, _Holder) and self.label == other.label

    def __hash__(self):
        return hash(self.label)


class TestFrozenIdentitySurjectionDict:
    """Tests for FrozenIdentitySurjectionDict class."""

    def test_init_empty(self):
        d = momapy.utils.FrozenIdentitySurjectionDict()
        assert len(d) == 0
        assert d.inverse == {}

    def test_inverse_keyed_by_id_not_value(self):
        a = _Holder("x")
        b = _Holder("x")
        assert a == b and a is not b
        d = momapy.utils.FrozenIdentitySurjectionDict({"k1": a, "k2": b})
        assert d.inverse[id(a)] == {"k1"}
        assert d.inverse[id(b)] == {"k2"}
        assert id(a) != id(b)

    def test_multiple_keys_same_value(self):
        a = _Holder("only")
        d = momapy.utils.FrozenIdentitySurjectionDict({"k1": a, "k2": a})
        assert d.inverse[id(a)] == {"k1", "k2"}

    def test_forward_dict_uses_eq(self):
        """Forward-dict semantics are unchanged: ``==`` keys collide."""
        d = momapy.utils.FrozenIdentitySurjectionDict({"k": 1})
        assert d["k"] == 1

    def test_immutable(self):
        d = momapy.utils.FrozenIdentitySurjectionDict({"k": 1})
        with pytest.raises(Exception):
            d["other"] = 2

    def test_pickle_roundtrip_rebuilds_inverse(self):
        import pickle

        a = _Holder("x")
        b = _Holder("x")
        d = momapy.utils.FrozenIdentitySurjectionDict({"k1": a, "k2": b})
        loaded = pickle.loads(pickle.dumps(d))
        # Forward dict equal under ==, but underlying value identities are
        # fresh: the rebuilt inverse keys must match the loaded values'
        # id()s, not the originals'.
        loaded_a = loaded["k1"]
        loaded_b = loaded["k2"]
        assert loaded.inverse[id(loaded_a)] == {"k1"}
        assert loaded.inverse[id(loaded_b)] == {"k2"}


def test_get_element_from_collection():
    """Test get_element_from_collection function."""
    collection = [1, 2, 3, 4]
    assert momapy.utils.get_element_from_collection(2, collection) == 2
    assert momapy.utils.get_element_from_collection(5, collection) is None


def test_get_or_return_element_from_collection():
    """Test get_or_return_element_from_collection function."""
    collection = [1, 2, 3, 4]
    assert momapy.utils.get_or_return_element_from_collection(2, collection) == 2
    assert momapy.utils.get_or_return_element_from_collection(5, collection) == 5


def test_make_uuid4_as_str():
    """Test make_uuid4_as_str function."""
    uuid1 = momapy.utils.make_uuid4_as_str()
    uuid2 = momapy.utils.make_uuid4_as_str()

    assert isinstance(uuid1, str)
    assert isinstance(uuid2, str)
    assert uuid1 != uuid2
    assert len(uuid1) == 36  # Standard UUID string length


def test_pretty_print_iterable_with_point():
    """pretty_print handles an iterable containing a Point without crashing.

    Regression: the iterable branch referenced ``momapy.geometry.Point`` while
    the module only did ``import momapy``, raising AttributeError in a minimal
    environment.
    """
    import momapy.geometry

    momapy.utils.pretty_print([momapy.geometry.Point(1, 2), 3])


def test_pretty_print_max_depth_none_is_unlimited(capsys):
    """max_depth=None recurses the whole structure; 0 stops at direct fields."""
    import dataclasses

    @dataclasses.dataclass
    class Leaf:
        value: int

    @dataclasses.dataclass
    class Mid:
        leaf: Leaf

    @dataclasses.dataclass
    class Root:
        mid: Mid

    root = Root(mid=Mid(leaf=Leaf(value=42)))

    momapy.utils.pretty_print(root, max_depth=0)
    shallow = capsys.readouterr().out
    assert "leaf" not in shallow

    momapy.utils.pretty_print(root, max_depth=None)
    unlimited = capsys.readouterr().out
    assert "leaf" in unlimited
    assert "value" in unlimited


class TestIdentityMultiDict:
    def test_empty_construction(self):
        d = momapy.utils.IdentityMultiDict()
        assert len(d) == 0
        assert dict(d.inverse) == {}

    def test_construct_from_mapping(self):
        a, b = object(), object()
        d = momapy.utils.IdentityMultiDict({"x": [a, b], "y": [a]})
        assert d["x"] == frozenset({a, b})
        assert d["y"] == frozenset({a})
        assert d.inverse[id(a)] == frozenset({"x", "y"})
        assert d.inverse[id(b)] == frozenset({"x"})

    def test_add_and_mapping_access(self):
        d = momapy.utils.IdentityMultiDict()
        a = object()
        d.add("x", a)
        assert d["x"] == frozenset({a})
        assert d.get("x", frozenset()) == frozenset({a})
        assert d.get("missing", frozenset()) == frozenset()
        assert d.inverse[id(a)] == frozenset({"x"})

    def test_getitem_missing_raises(self):
        d = momapy.utils.IdentityMultiDict()
        with pytest.raises(KeyError):
            d["missing"]

    def test_setitem_raises(self):
        """``d[k] = v`` must raise: the corruption guard holds (not a dict)."""
        d = momapy.utils.IdentityMultiDict()
        with pytest.raises(TypeError):
            d["x"] = object()

    def test_add_multiple_values(self):
        d = momapy.utils.IdentityMultiDict()
        a, b = object(), object()
        d.add("x", a)
        d.add("x", b)
        assert d["x"] == frozenset({a, b})

    def test_replace_value(self):
        d = momapy.utils.IdentityMultiDict()
        a, b, c = object(), object(), object()
        d.add("x", a)
        d.add("y", a)
        d.add("z", b)
        d.replace_value(a, c)
        assert d["x"] == frozenset({c})
        assert d["y"] == frozenset({c})
        assert d["z"] == frozenset({b})
        assert d.inverse[id(c)] == frozenset({"x", "y"})
        assert id(a) not in d.inverse

    def test_replace_value_chained(self):
        """Two evictions under the same key collapse to a single survivor."""
        d = momapy.utils.IdentityMultiDict()
        a, b, c = object(), object(), object()
        d.add("k", a)
        d.replace_value(a, b)
        d.replace_value(b, c)
        assert d["k"] == frozenset({c})
        assert d.inverse[id(c)] == frozenset({"k"})

    def test_remove(self):
        d = momapy.utils.IdentityMultiDict()
        a, b = object(), object()
        d.add("x", a)
        d.add("x", b)
        d.remove("x", a)
        assert d["x"] == frozenset({b})
        assert id(a) not in d.inverse

    def test_contains_and_iter(self):
        a = object()
        d = momapy.utils.IdentityMultiDict({"x": [a]})
        assert "x" in d
        assert "y" not in d
        assert set(d) == {"x"}
        assert set(d.keys()) == {"x"}


class TestFrozenIdentityMultiDict:
    def test_construct_from_mapping(self):
        a, b = object(), object()
        d = momapy.utils.FrozenIdentityMultiDict({"x": [a, b], "y": [a]})
        assert d["x"] == frozenset({a, b})
        assert d.get("y", frozenset()) == frozenset({a})
        assert d.inverse[id(a)] == frozenset({"x", "y"})
        assert d.inverse[id(b)] == frozenset({"x"})

    def test_empty_construction(self):
        d = momapy.utils.FrozenIdentityMultiDict()
        assert len(d) == 0
        assert dict(d.inverse) == {}

    def test_values_and_items(self):
        a, b = object(), object()
        d = momapy.utils.FrozenIdentityMultiDict({"x": [a, b]})
        assert list(d.values()) == [frozenset({a, b})]
        assert dict(d.items()) == {"x": frozenset({a, b})}


def _all_family_instances():
    """One constructed instance of each of the six mapping classes."""
    shared = object()
    return [
        momapy.utils.SurjectionDict({"a": 1, "b": 1, "c": 2}),
        momapy.utils.IdentitySurjectionDict({"a": shared, "b": shared}),
        momapy.utils.FrozenSurjectionDict({"a": 1, "b": 1, "c": 2}),
        momapy.utils.FrozenIdentitySurjectionDict({"a": shared, "b": shared}),
        momapy.utils.IdentityMultiDict({"a": [shared], "b": [shared]}),
        momapy.utils.FrozenIdentityMultiDict({"a": [shared], "b": [shared]}),
    ]


class TestInverseFamilyInvariants:
    """Cross-family invariants on the uniform ``.inverse`` contract."""

    def test_inverse_is_frozendict_of_frozensets(self):
        for d in _all_family_instances():
            inverse = d.inverse
            assert isinstance(inverse, frozendict.frozendict)
            for bucket in inverse.values():
                assert isinstance(bucket, frozenset)

    def test_frozen_inverse_is_immutable(self):
        shared = object()
        frozen_instances = [
            momapy.utils.FrozenSurjectionDict({"a": 1, "b": 1}),
            momapy.utils.FrozenIdentitySurjectionDict({"a": shared, "b": shared}),
            momapy.utils.FrozenIdentityMultiDict({"a": [shared]}),
        ]
        for d in frozen_instances:
            inverse = d.inverse
            some_key = next(iter(inverse))
            with pytest.raises(TypeError):
                inverse[some_key] = "x"
            bucket = inverse[some_key]
            assert not hasattr(bucket, "add")

    def test_frozen_identity_surjection_inverse_no_leak(self):
        """Regression: the returned inverse must not expose live state.

        ``LayoutModelMapping`` is a ``FrozenIdentitySurjectionDict``; a
        caller mutating a bucket or deleting a key from ``.inverse`` must
        not corrupt the frozen object's index.
        """
        a = object()
        d = momapy.utils.FrozenIdentitySurjectionDict({"x": a, "y": a})
        bucket = d.inverse[id(a)]
        assert bucket == frozenset({"x", "y"})
        with pytest.raises(AttributeError):
            bucket.add("z")
        assert d.inverse[id(a)] == frozenset({"x", "y"})

    def test_mutable_surjection_inverse_is_snapshot(self):
        d = momapy.utils.SurjectionDict({"a": 1})
        snapshot = d.inverse
        d["b"] = 1
        assert snapshot[1] == frozenset({"a"})
        assert d.inverse[1] == frozenset({"a", "b"})

    def test_mutable_identity_multidict_inverse_is_snapshot(self):
        a = object()
        d = momapy.utils.IdentityMultiDict({"a": [a]})
        snapshot = d.inverse
        d.add("b", a)
        assert snapshot[id(a)] == frozenset({"a"})
        assert d.inverse[id(a)] == frozenset({"a", "b"})

    def test_surjection_set_bucket_no_duplicate(self):
        d = momapy.utils.SurjectionDict()
        d["a"] = 1
        d["a"] = 1
        assert d.inverse[1] == frozenset({"a"})

    def test_surjection_emptied_bucket_dropped(self):
        """Re-pointing the last key off a value drops the emptied bucket."""
        d = momapy.utils.SurjectionDict({"a": 1})
        d["a"] = 2
        assert 1 not in d.inverse
        assert d.inverse[2] == frozenset({"a"})

    def test_multidict_read_mapping_parity(self):
        a, b = object(), object()
        data = {"x": [a, b], "y": [a]}
        mutable = momapy.utils.IdentityMultiDict(data)
        frozen = momapy.utils.FrozenIdentityMultiDict(data)
        for key in ("x", "y"):
            assert mutable[key] == frozen[key]
            assert mutable.get(key, frozenset()) == frozen.get(key, frozenset())
        assert set(mutable.keys()) == set(frozen.keys())
        assert set(mutable.values()) == set(frozen.values())
        assert dict(mutable.items()) == dict(frozen.items())
        assert mutable.get("missing", frozenset()) == frozenset()
        assert frozen.get("missing", frozenset()) == frozenset()
