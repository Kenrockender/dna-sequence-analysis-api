# DNA Sequence Analysis API - Submission Summary

**Project:** Bioinformatics Engineer Intern Technical Test
**Repository:** https://github.com/Kenrockender/bioinformatics-test
**Date:** 2026-10-21

## Required deliverables

- `POST /api/align`: global alignment against the server-loaded `REF_001` reference, with SNV, insertion, and deletion calls.
- `POST /api/translate`: standard-code translation in frames 1-3, including `N` to `X`, trailing-codon, and stop-codon rules.
- Shared FASTA validation: one record, A/C/G/T/N only, 1-1,000 nt, case normalization, and clear JSON validation responses.
- Documentation: setup, API examples, scoring, coordinates, assumptions, limitations, and reproducible tests are in `README.md`.
- Meaningful incremental Git history and pinned dependencies in `requirements.txt`.

## Verification

Run:

```bash
pytest -q
```

The suite covers all supplied patient FASTAs through the required endpoints, malformed and multiple-record FASTA, lowercase/multiline input, `N`-containing codons, frames, stops, incomplete codons, length limits, coordinate/grouping rules, and the optional combined-analysis endpoint.

## Optional additions included

- Browser UI at `/` for uploads, sample inputs, alignment, translation, and combined analysis.
- `POST /api/analyze` for optional variant-effect annotation.
- Dockerfile for containerized execution.

## Notes

Alignment uses Biopython's global `PairwiseAligner` with match `+1`, mismatch `-1`, linear gap `-2` per base, and `N` scoring `0`. The implementation returns the first deterministic optimal alignment from Biopython; equivalent indel placements may differ in ambiguous regions.
