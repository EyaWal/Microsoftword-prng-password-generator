# Word PRNG Password Generator

🎬 Inspired by a hilarious video short I saw on YouTube [link](https://www.youtube.com/shorts/T2lgRadzk-0),
I decided to create a quirky but secure password generator… using Word documents!

Yes, you read that right. Instead of just using Python's random numbers, this tool **mutates Word documents** to cook up passwords. Think of it like giving your Word files a little chaos party, and the password is the VIP that comes out at the end. 🎉

---

## Where the idea came from

1. **The starting point**: a YouTube short, and the thought of using Word as a random number generator.
2. **A real observation**: when you insert an image in the middle of a Word paragraph, the text gets cut, pieces get shuffled, the layout goes wild. Chaos! We first wanted to *measure that chaos, just out of curiosity*.
3. **Then a second thought**: why not make a password out of it?
4. **First version**: random text and random images dropped into paragraphs, then a hash of the content. It worked, but it missed the point: the chaos was *injected*, not *born from the manipulation itself*.
5. **Current version**: we really **cut existing text in two** and drop the image or text inside the cut (like Word does), we **measure the mess** with a chaos score, and we mix the mutated document with real cryptographic randomness.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/word-prng-password-generator.git
cd word-prng-password-generator
```
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

```bash
python password_generator.py --docs template.docx template2.docx \
  --images sample1.jpg sample2.png --n_passwords 5 --length 16 --verbose
```

- `--docs`: list of .docx files to use as the base (their text is merged)
- `--images`: list of images for mutations (optional)
- `--output`: name of the mutated Word file, last one is kept (default: `mutated.docx`)
- `--n_passwords`: number of passwords to generate
- `--length`: length of each password
- `--verbose`: tell the chaos party live

Example output:

```
Party #1
   « Paragra » + IMAGE + « ph original number 3. »
   « Orig » + k3Fz9 + « inal paragraph number 1. »

Generated passwords:
  7Qe!aT2uYw$9LmXc   (chaos 45/100: fragmentation +120%, XML bloat +58%)
```

## How it works (aka "The Chaos Party")

Imagine your Word documents as party guests. 📝
Each guest gets a little chaos:

1. **Cut**: a piece of text is picked at random and cut in two, in the middle of a word or a sentence.
2. **Crash**: a random image or a few random characters land right in the cut. 🖼️
3. **Measure**: we compare the document before and after and compute the **chaos score**.
4. **Snapshot**: the whole mutated document is hashed, and mixed with 32 bytes from `secrets`.
5. **VIP**: the seed becomes a password. Each password starts from a fresh copy of your documents.

### The chaos score (0-100)

Two simple measures, half of the score each:

- **Fragmentation**: how many extra pieces of text (called *runs* in Word's XML) were created.
- **XML bloat**: how much the XML grew compared to the visible text.

## Is it really secure?

Honest answer: **the security comes from `secrets`, not from Word.** The chaos (which piece gets cut, where, with what) is driven by Python's `random`, which is not a safe source. So the document makes the idea fun and the score interesting, while `secrets.token_bytes` is what makes each password unpredictable. Characters are also picked without bias (rejection sampling instead of a plain modulo).

## Tests

```bash
pip install pytest
pytest
```

## Ideas for later

- Try other chaos measures (entropy of the piece lengths, images moving around).
- Measure chaos on real Word edits (before/after a human manipulation) instead of simulated ones.
- A small web interface (a first version exists, set aside to keep the project simple).