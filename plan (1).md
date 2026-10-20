# Plan: DNA Sequence Analysis API (Bioinformatics Engineer Intern test)

Owner: Kenneth Flynn · Time allowed by the test: 3 days · Status: **plan only, nothing built yet**

---

## 1. Goal

Build a small REST API in Python that takes one FASTA file and either:

1. **aligns** it to the supplied reference (`REF_001`, 300 bp) and reports variants, or
2. **translates** it to protein in reading frame 1, 2 or 3.

On top of that, the test grades engineering quality: clean structure, git history, tests, README. I am also doing all three optional bonuses.

## 2. Decisions made (from our Q&A)

| Topic | Decision |
|---|---|
| Framework | **FastAPI** (Pydantic schemas, automatic `/docs`, easy router/service/schema split) |
| Algorithms | **Biopython directly** (`PairwiseAligner` for alignment, Biopython codon table for the genetic code). Trade-off: I give up the "implement it yourself without bioinformatics libraries" bonus. |
| Gap scoring | **Linear**: match +1, mismatch -1, gap -2 per gap character, **N vs anything = 0**. Reproduces the test's example score for `patient_02` (294.0). |
| Bonuses | Web UI, Dockerfile, `POST /api/analyze` |
| Web UI | Plain HTML/CSS/JS, served by the same FastAPI app (no build step) |
| Code style | Readable, short comments explaining *why* (coordinates, N handling). README has a "design decisions" section I can talk through in an interview. |
| Delivery | Zip with `.git` folder and step-by-step commit history. I push it to my own public GitHub repo. |
| Git author | Kenneth Flynn `<kenneth.flynn.g@gmail.com>`, no co-author trailer |

## 3. Proposed defaults (change anything you disagree with)

| Topic | Default | Why |
|---|---|---|
| Error status code | **422** for every invalid-input case (missing file, bad FASTA, bad frame, too long) | The test accepts 400 or 422. One rule is easier to document and test. |
| Error body | `{"error": "<machine_code>", "detail": "<human message>"}` | Clear JSON; `detail` also matches FastAPI's usual key. |
| `identity` | Full-precision float, not rounded | Avoids tolerance problems if a checker compares values. |
| Python | 3.11+ (3.13 is what I would test with here) | |
| Tests | `pytest` with FastAPI `TestClient` | |
| Dependencies | One `requirements.txt` with runtime and test packages, pinned versions | The test asks for one file that covers running the API and the tests. |

## 4. Project layout

```
dna-analysis-api/
├── app/
│   ├── main.py            # creates the FastAPI app, error handlers, mounts the UI
│   ├── config.py          # constants: MAX_LEN=1000, scoring, reference path
│   ├── errors.py          # one custom exception (code + message) -> JSON 422
│   ├── schemas.py         # Pydantic response models
│   ├── routers/
│   │   ├── align.py       # POST /api/align
│   │   ├── translate.py   # POST /api/translate
│   │   └── analyze.py     # POST /api/analyze  (bonus)
│   ├── services/
│   │   ├── fasta.py       # parse + validate FASTA (shared by all endpoints)
│   │   ├── reference.py   # loads reference.fasta once at startup
│   │   ├── alignment.py   # Biopython aligner + identity + variant extraction
│   │   ├── translation.py # frame handling, N -> X, stop handling
│   │   └── effects.py     # variant effect annotation (bonus)
│   └── data/reference.fasta
├── static/                # index.html, app.js, style.css, samples/*.fasta  (bonus UI)
├── tests/                 # see section 8
├── requirements.txt
├── Dockerfile  .dockerignore  .gitignore
└── README.md
```

Rule: routers only handle HTTP (read upload, call a service, return a model). All logic lives in `services/`, so it can be unit-tested without HTTP.

## 5. API contract

### Shared FASTA validation (`services/fasta.py`)

- Exactly **one** record. The header (text after `>`) must be non-empty.
- Sequence is 1 to 1,000 nt after joining lines and trimming surrounding whitespace.
- Only `A C G T N`, case-insensitive. Convert to uppercase. `N` is valid, even if the sequence is mostly N.
- Multiline sequences and blank lines are allowed. Trailing or leading whitespace on a line is ignored.
- Reject: other characters (`U`, `R`, `-`, digits, `*`), whitespace **inside** a sequence line (`ATG CCC`), empty sequence, second `>` record, text before the first header, non-UTF-8 content, over-length sequences. A byte-size guard (about 1 MiB) stops absurd uploads from being read into memory.
- `sequence_id` = first whitespace-delimited token after `>`.
- Windows line endings (`\r\n`) and a UTF-8 BOM are tolerated.

### `POST /api/align`

Input: multipart form with `file`. Output matches the test's example:

```json
{
  "sequence_id": "patient_02",
  "reference_id": "REF_001",
  "alignment": {"score": 294.0, "identity": 0.99,
                "reference_aligned": "...", "query_aligned": "..."},
  "variants": [{"position": 52, "ref": "C", "alt": "A", "type": "SNV"}]
}
```

### `POST /api/translate`

Input: multipart form with `file` and optional `frame` (1, 2 or 3, default 1). Output: `sequence_id`, `frame`, `protein`, `length`, `has_stop_codon`.

- `frame` must be a plain integer 1 to 3. `0`, `4`, `abc`, `1.5` and empty string all give 422.

### `POST /api/analyze` (bonus)

Input: multipart form with `file`. Output: the `/api/align` fields plus `query_translation`, `reference_translation` (frame 1), and an `effect` block on every variant (section 6.5).

### Errors

Missing file, malformed FASTA and bad frame all return 422 with the JSON body from section 3. FastAPI's own validation errors go through the same handler so the format never changes.

## 6. Core rules (the parts most likely to be graded)

### 6.1 Alignment

- Global alignment (Needleman-Wunsch) via `Bio.Align.PairwiseAligner`, mode `global`.
- Scoring: custom substitution matrix over `ACGTN` (match +1, mismatch -1, anything with N = 0). Open and extend gap score are both -2, so gaps are **linear**, and **end gaps are penalised too**.
- Take the score from the aligner's `.score` (cheap) and the first alignment from the iterator. Do **not** call `len(alignments)`: it can overflow when there are many ties.
- **Tie rule (to document in README):** Biopython returns optimal alignments in a fixed order and I always take the first. Output is deterministic. Equivalent indel placements are allowed by the test.
- `identity` = columns where both bases are identical A/C/G/T ÷ total alignment columns. Gap columns and N columns count in the denominator and never count as a match.

### 6.2 Variant extraction (walk the two aligned strings)

```
ref_pos = 0
for each column:
    both bases        -> ref_pos += 1; if both in ACGT and differ: SNV at ref_pos
    ref is '-'        -> run of '-' in ref  = ONE insertion
                         position = ref_pos (the preceding reference base; 0 = before base 1)
                         ref = "-", alt = the inserted bases
    query is '-'      -> run of '-' in query = ONE deletion
                         position = ref_pos + 1 (first deleted base)
                         ref = deleted bases, alt = "-"; then ref_pos += run length
```

- Events come out in alignment order, so they are already sorted by position.
- An N in either base is never an SNV. Gaps next to N runs are still reported; the README lists this as a limitation (the placement of an indel inside a run of N is arbitrary).

### 6.3 Translation

- Frame 1/2/3 means start at nucleotide 1/2/3 of the supplied strand. No start-codon search, no reverse complement.
- Only complete codons; leftover 1 or 2 nt are ignored.
- Any codon containing N becomes `X`, **even if the amino acid could be inferred** (for example `GGN`). Biopython's `Seq.translate()` would infer it, so I loop over codons myself and use Biopython's codon *table* only for the genetic code.
- Stop at the first unambiguous stop (TAA, TAG, TGA); `*` is not included; `has_stop_codon` is true only if one was hit. `length = len(protein)` including `X`.
- No complete codon available → `protein: ""`, `length: 0`, `has_stop_codon: false`.

### 6.4 Reference

Loaded once at startup from `app/data/reference.fasta` through the **same** FASTA parser, so `reference_id` is `REF_001` from the header.

### 6.5 Variant effects (`/api/analyze`, bonus)

Everything is judged against **reference frame 1**.

| Variant | Rule |
|---|---|
| SNV | Take the reference codon and the aligned query codon. Same amino acid → `synonymous`; different → `missense`; new stop (ref was not a stop) → `nonsense`; ref stop became non-stop → `stop_lost` (my own extra label). |
| Insertion / deletion | Length divisible by 3 → `inframe_insertion` / `inframe_deletion`; otherwise `frameshift`. |
| Several SNVs in one codon | Evaluated **together** as one alt codon; each variant reports the combined result and a note. |
| Codon contains N, or an indel inside the same codon as an SNV | `undetermined`, with a reason. |
| Variant after an uncompensated upstream frameshift | `undetermined` ("downstream of frameshift"). If a later indel brings the running offset back to 0 mod 3, later variants are annotated normally again. |
| Each SNV also reports | `codon`, `ref_codon`, `alt_codon`, `ref_aa`, `alt_aa`, `aa_change` (e.g. `K59N`). |

Documented limitation: an indel is classified from its own length plus the running offset. It does not try to model every nearby combination.

## 7. What I expect for the sample files

I diffed these by eye from the FASTA files. The tests will confirm them, so please treat these as expectations, not facts.

| File | Expected variants | Notes |
|---|---|---|
| `patient_01` | none | Identical to reference. Score 300.0, identity 1.0. |
| `patient_02` | SNV 52 C→A, 177 A→T, 245 T→G | Matches the test's example (score 294.0, identity 0.99). Effects: codon 18 CGA→AGA **synonymous**, codon 59 AAA→AAT **missense** (K59N), codon 82 TTA→TGA **nonsense**. Translation stops at length 81. |
| `patient_03` | deletion 106 `AAC`→`-` (3 bp, codon 36, in-frame); deletion 208 `A`→`-` (1 bp, frameshift) | 296 nt long. Linear score 288.0 (296 matches − 4 gaps × 2), identity 296/300. |
| `patient_04` | none | Several long N runs. N is never an SNV. Identity is well below 1; N-containing codons translate to `X`. |
| `patient_05` | insertion at 18 `-`→`ATC` (in-frame); insertion at 230 `-`→`T` (frameshift) | 304 nt long. Linear score 292.0, identity 300/304. |

## 8. Test plan

Run with `pytest -v`. Structure:

| File | Covers |
|---|---|
| `test_fasta.py` | valid, lowercase → uppercase, multiline, blank lines, CRLF, header token extraction; rejects: empty seq, header only, no header, multiple records, invalid char, embedded whitespace, empty file, exactly 1,000 nt accepted, 1,001 nt rejected |
| `test_translation.py` | frames 1/2/3 on a hand-made sequence; trailing 1 and 2 nt ignored; no complete codon → empty protein; first stop ends translation; stop not in output; `has_stop_codon` true/false; N codon → `X` (including `GGN`); stop codon with N (`TAN`) is not a stop |
| `test_variants.py` | hand-built aligned strings: SNV; insertion at position 0 and mid-sequence; deletion at position 1; multi-base indel grouped as one event; two separate indels; adjacent SNV + indel; N is not an SNV; event ordering |
| `test_align_api.py` | all five patient files (exact variants, score, identity); the aligned strings with gaps removed equal the original sequences; **applying the returned variants to the reference reproduces the query** (for N-free input); determinism; lowercase input; 422s |
| `test_translate_api.py` | patient_02 expected protein; each frame; N codons; incomplete final codon; invalid frame values; missing file; multi-record; length limit |
| `test_analyze_api.py` | patient_02 → synonymous, missense, nonsense; patient_03 → in-frame deletion + frameshift; patient_05 → in-frame insertion + frameshift; N codon → undetermined; downstream-of-frameshift rule |
| Oracle check | a tiny pure-Python Needleman-Wunsch in the tests recomputes the score on small random cases to confirm Biopython's scoring set-up (end gaps, N = 0) |

The README will include the terminal output of the final test run.

## 9. Git commit plan (small, meaningful commits)

1. `chore: project skeleton, requirements, gitignore, reference and sample data`
2. `feat: FASTA parsing and validation service`
3. `test: FASTA validation cases`
4. `feat: protein translation service`
5. `test: translation frames, stops, N codons, incomplete codons`
6. `feat: global alignment and variant extraction`
7. `test: variant coordinates, grouping and scoring`
8. `feat: /api/align and /api/translate with JSON error handling`
9. `test: endpoint tests for all patient files`
10. `docs: first README (install, run, curl examples)`
11. `feat: /api/analyze variant effect annotation` + tests
12. `feat: web interface`
13. `chore: Dockerfile and .dockerignore`
14. `docs: finalise README with conventions, limitations and test output`

Commit timestamps will be real. I will not back-date anything.

## 10. Web UI (bonus)

One page: pick or drag a FASTA file → choose **Align / Translate / Analyze** → frame selector appears only for Translate → **Run**.

- Align result: score and identity, variant table, alignment viewer in 60-column blocks with mismatches and gaps highlighted.
- Translate result: protein (wrapped), length, stop-codon flag.
- Analyze result: variant table with effect labels.
- Any API error appears in a visible error box with the server's message.
- "Load sample" dropdown with the five patient files so a reviewer can try it with one click.
- Must work on a phone-width screen and in dark mode.

## 11. Dockerfile (bonus)

`python:3.12-slim`, install `requirements.txt`, copy `app/` and `static/`, run as non-root, `uvicorn app.main:app --host 0.0.0.0 --port 8000`, `EXPOSE 8000`. This sandbox may not have a running Docker daemon; if I cannot build it here I will say it is untested rather than claim it works.

## 12. README outline

1. What it does · 2. Install (venv + `pip install -r requirements.txt`) · 3. Run (uvicorn) · 4. Web UI and `/docs` · 5. curl examples for all three endpoints · 6. Run tests (one command) + pasted output · 7. Scoring, identity and variant conventions · 8. Tie-breaking rule · 9. Assumptions · 10. Limitations (N regions, nearby-variant effects, Biopython not hand-written) · 11. Docker usage · 12. Design decisions.

## 13. Risks and things to watch

- **Coordinates are the easy place to lose marks**: deletion = first deleted base; insertion = preceding base (0 = before base 1). Covered by hand-built tests.
- **Biopython translate infers amino acids from partial N codons**, which the test forbids. Handled by my own codon loop.
- **Tie placement of indels** can differ between tools. I document the rule and test round-trip invariants, not just exact positions.
- **`identity` denominators**: include gap and N columns.
- **Don't promise what I did not run**: Docker build and the UI will be tested before I say they work.
- Honest note for the interview: alignment and translation are Biopython-backed. The parts that are mine are the validation, N rules, variant extraction and effect annotation.

## 14. Order of work and definition of done

1. Environment and skeleton → 2. FASTA → 3. translation → 4. alignment and variants → 5. API and error handling → 6. required tests green → 7. README v1 → 8. analyze → 9. UI → 10. Dockerfile → 11. final README with test output → 12. end-to-end check with `curl` and the UI → 13. zip with `.git`.

**Done when:** both required endpoints pass tests for all five patient files and every case in the test's checklist; README is complete; git log shows the steps above; bonuses work or are clearly marked untested.

## 15. Open questions for you

- Are 422 for all errors and the `{"error", "detail"}` body fine, or do you prefer 400 for malformed FASTA?
- Do you want the repo named something specific (e.g. `dna-analysis-api`)?
- Any employer rule on AI assistance I should reflect in the README (for example a short "how I built this" note)?
- Should I start building now, or do you want to edit this plan first?
