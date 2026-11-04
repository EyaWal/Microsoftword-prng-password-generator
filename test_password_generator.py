import string

import docx
import pytest

from password_generator import (
    chaos_score,
    generate_super_secure_passwords,
    insert_image,
    insert_random_text,
    seed_to_password,
    snapshot,
    snapshot_seed,
)


@pytest.fixture
def source_path(tmp_path):
    path = tmp_path / "source.docx"
    doc = docx.Document()
    for i in range(1, 6):
        doc.add_paragraph(f"Original paragraph number {i}.")
    doc.save(path)
    return str(path)


@pytest.fixture
def doc(source_path):
    return docx.Document(source_path)


@pytest.fixture
def image(tmp_path):
    from PIL import Image

    path = tmp_path / "square.png"
    Image.new("RGB", (30, 30), color=(200, 50, 80)).save(path)
    return str(path)


def test_cut_fragments_the_text(doc):
    before = snapshot(doc)
    insert_random_text(doc)
    assert snapshot(doc)["runs"] > before["runs"]


def test_most_paragraphs_stay_intact(doc):
    insert_random_text(doc)
    intact = [p.text for p in doc.paragraphs
              if p.text.startswith("Original paragraph number") and p.text.endswith(".")]
    assert len(intact) >= 4


def test_image_is_inserted(doc, image):
    insert_image(doc, image)
    assert len(doc.inline_shapes) == 1


def test_chaos_score_grows_with_mutations(doc):
    before = snapshot(doc)
    insert_random_text(doc)
    one = chaos_score(before, snapshot(doc))["score"]
    for _ in range(8):
        insert_random_text(doc)
    many = chaos_score(before, snapshot(doc))["score"]
    assert 0 <= one <= many <= 100


def test_password_length_and_charset(doc):
    insert_random_text(doc)
    password = seed_to_password(snapshot_seed(doc), length=24, chars=string.ascii_lowercase)
    assert len(password) == 24
    assert all(c in string.ascii_lowercase for c in password)


def test_same_document_gives_different_seeds(doc):
    insert_random_text(doc)
    # Real randomness from `secrets` is mixed in every time
    assert snapshot_seed(doc) != snapshot_seed(doc)


def test_end_to_end(source_path, image, tmp_path):
    output = str(tmp_path / "mutated.docx")
    results = generate_super_secure_passwords([source_path], [image], output,
                                              n_passwords=3, length=20)
    assert len(results) == 3
    assert all(len(r["password"]) == 20 for r in results)
    assert len({r["password"] for r in results}) == 3
    docx.Document(output)  # the mutated document still opens