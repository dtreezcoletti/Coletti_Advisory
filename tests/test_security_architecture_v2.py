import os

from coletti_advisory.storage import (
    KEY_DERIVATION_SCHEME,
    SECURITY_ARCHITECTURE_VERSION,
    EncryptedLocalDemoStorage,
    derive_scoped_key,
)


def test_scoped_data_key_is_not_root_key_and_is_deterministic():
    root = os.urandom(32)
    kwargs = {
        "purpose": "source-object",
        "organization_id": "org-1",
        "engagement_id": "eng-1",
        "object_id": "SRC-1",
        "key_version": "v1",
    }
    first = derive_scoped_key(root, **kwargs)
    second = derive_scoped_key(root, **kwargs)

    assert len(first) == 32
    assert first != root
    assert first == second


def test_scoped_keys_are_domain_separated_by_engagement_object_and_purpose():
    root = b"r" * 32
    common = {
        "organization_id": "org-1",
        "key_version": "v1",
    }
    source_a = derive_scoped_key(
        root,
        purpose="source-object",
        engagement_id="eng-1",
        object_id="SRC-1",
        **common,
    )
    source_b = derive_scoped_key(
        root,
        purpose="source-object",
        engagement_id="eng-2",
        object_id="SRC-1",
        **common,
    )
    source_c = derive_scoped_key(
        root,
        purpose="source-object",
        engagement_id="eng-1",
        object_id="SRC-2",
        **common,
    )
    publication = derive_scoped_key(
        root,
        purpose="publication-state",
        engagement_id="eng-1",
        object_id="publication-state",
        **common,
    )

    assert len({source_a, source_b, source_c, publication}) == 4


def test_stored_object_records_non_secret_security_profile(tmp_path):
    storage = EncryptedLocalDemoStorage(tmp_path, b"k" * 32, key_version="v1")
    result = storage.put(
        organization_id="org-1",
        engagement_id="eng-1",
        source_id="SRC-1",
        filename="synthetic.txt",
        data=b"synthetic payload",
    )

    assert result.security_architecture == SECURITY_ARCHITECTURE_VERSION
    assert result.key_derivation == KEY_DERIVATION_SCHEME
    assert result.key_version == "v1"
