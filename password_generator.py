#!/usr/bin/env python3
"""
Word PRNG Password Generator
============================

Idea: when you insert an image in the middle of a Word paragraph, the text gets
cut and the document becomes "chaotic". We provoke that on purpose, measure it
(a chaos score from 0 to 100), and use the mutated document as an ingredient
of a password.

The party in 4 steps:
  insert_image / insert_random_text  ->  cut a piece of text and drop something in
  chaos_score                        ->  measure the mess (before vs after)
  snapshot_seed                      ->  hash of the mutated document + real randomness
  seed_to_password                   ->  turn the seed into characters
"""

import argparse
import copy
import hashlib
import io
import random
import secrets
import string

import docx
from docx.shared import Inches
from docx.text.run import Run

CHARS = string.ascii_letters + string.digits + "!@#$%&*"

# ---------------- The chaos party ----------------


def _text_runs(doc):
    """All the pieces of text (runs) we are allowed to cut."""
    return [r for p in doc.paragraphs for r in p.runs if len(r.text) >= 2]


def _cut_and_insert(doc, make_run):
    """Cut one text run in two, at a random point, and drop a new run in the cut.

    This is what Word does when you insert something in the middle of a sentence.
    Returns the two pieces of text (left, right) for the journal.
    """
    runs = _text_runs(doc)
    if not runs:
        doc.add_paragraph("Placeholder text")
        runs = _text_runs(doc)

    run = random.choice(runs)
    paragraph = run._parent
    cut = random.randint(1, len(run.text) - 1)
    left, right = run.text[:cut], run.text[cut:]

    # The run is split in two, both halves keep the formatting
    right_xml = copy.deepcopy(run._r)
    run.text = left
    Run(right_xml, paragraph).text = right
    run._r.addnext(right_xml)

    # What crashes the party goes right in the cut
    new_run = make_run(paragraph)
    run._r.addnext(new_run._r)
    return left, right


def insert_image(doc, img_path):
    """Cut a piece of text and drop an image in the cut."""
    def make_run(paragraph):
        run = paragraph.add_run()
        run.add_picture(img_path, width=Inches(1.5))
        return run

    left, right = _cut_and_insert(doc, make_run)
    return f"« {left} » + IMAGE + « {right} »"


def insert_random_text(doc, n_chars=5):
    """Cut a piece of text and drop random characters in the cut."""
    random_text = "".join(random.choices(string.ascii_letters + string.digits, k=n_chars))
    left, right = _cut_and_insert(doc, lambda paragraph: paragraph.add_run(random_text))
    return f"« {left} » + {random_text} + « {right} »"


# ---------------- The chaos score ----------------


def snapshot(doc):
    """Photo of the document: number of runs, XML weight, visible text."""
    return {
        "runs": len(doc.element.xpath("//w:r")),
        "xml": len(doc.element.xml),
        "text": sum(len(p.text) for p in doc.paragraphs),
    }


def chaos_score(before, after):
    """How messy did the document get? Compares two snapshots (0-100).

    - fragmentation: how many extra text pieces (runs) were created
    - bloat: how much the XML grew compared to the visible text
    The score is the average of both. Each one goes through x / (1 + x): it climbs
    fast at first, then flattens, and never jumps straight to 100.
    """
    fragmentation = (after["runs"] - before["runs"]) / max(1, before["runs"])
    weight_before = before["xml"] / max(1, before["text"])
    weight_after = after["xml"] / max(1, after["text"])
    bloat = max(0, (weight_after - weight_before) / weight_before)

    def soften(x):
        return x / (1 + x)

    score = 50 * soften(fragmentation) + 50 * soften(bloat)
    return {"score": round(score), "fragmentation": fragmentation, "bloat": bloat}


# ---------------- From chaos to password ----------------


def snapshot_seed(doc):
    """Hash of the mutated document, mixed with 32 bytes of real randomness.

    The chaos itself comes from Python's `random`, so it is NOT a safe source of
    randomness. The real security comes from `secrets`. The chaos is the idea and
    the flavour, `secrets` is the safety.
    """
    buffer = io.BytesIO()
    doc.save(buffer)
    return hashlib.sha256(buffer.getvalue() + secrets.token_bytes(32)).digest()


def seed_to_password(seed, length=16, chars=CHARS):
    """Turn a seed into a password, without favouring some characters.

    A plain `% len(chars)` slightly favours the first characters, so we throw
    away the bytes that would cause it (rejection sampling).
    """
    n = len(chars)
    limit = 256 - (256 % n)
    stream = hashlib.shake_256(seed).digest(length * 20)
    return "".join(chars[b % n] for b in stream if b < limit)[:length]


def generate_super_secure_passwords(doc_paths, image_paths, output_doc_path,
                                    n_passwords=5, length=16,
                                    max_images=3, max_text_mutations=5,
                                    verbose=False):
    results = []

    for i in range(n_passwords):
        # Fresh copy of the first document for each password: titles, lists, tables
        # and formatting are kept. The text of the other documents is added at the end.
        doc = docx.Document(doc_paths[0])
        for path in doc_paths[1:]:
            for p in docx.Document(path).paragraphs:
                doc.add_paragraph(p.text)
        if not _text_runs(doc):
            doc.add_paragraph("Placeholder text")

        before = snapshot(doc)
        if verbose:
            print(f"\nParty #{i + 1}")

        # Random images crash the party
        for _ in range(random.randint(1, max_images)):
            if image_paths:
                line = insert_image(doc, random.choice(image_paths))
                if verbose:
                    print("  ", line)

        # Random text too
        for _ in range(random.randint(1, max_text_mutations)):
            line = insert_random_text(doc, random.randint(3, 12))
            if verbose:
                print("  ", line)

        chaos = chaos_score(before, snapshot(doc))
        password = seed_to_password(snapshot_seed(doc), length)
        results.append({"password": password, "chaos": chaos})

        doc.save(output_doc_path)  # only the last mutated document is kept

    return results


# ---------------- CLI ----------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Word-based PRNG Password Generator")
    parser.add_argument("--docs", nargs="+", required=True, help="List of .docx source files")
    parser.add_argument("--images", nargs="+", default=[], help="List of images for mutations")
    parser.add_argument("--output", default="mutated.docx", help="Output Word file after mutations")
    parser.add_argument("--n_passwords", type=int, default=5, help="Number of passwords to generate")
    parser.add_argument("--length", type=int, default=16, help="Length of each password")
    parser.add_argument("--verbose", action="store_true", help="Tell the chaos party live")

    args = parser.parse_args()

    results = generate_super_secure_passwords(
        args.docs, args.images, args.output, args.n_passwords, args.length,
        verbose=args.verbose,
    )

    print("\nGenerated passwords:")
    for r in results:
        c = r["chaos"]
        print(f"  {r['password']}   (chaos {c['score']}/100: "
              f"fragmentation +{c['fragmentation']:.0%}, XML bloat +{c['bloat']:.0%})")
    print(f"\nLast mutated document saved as: {args.output}")