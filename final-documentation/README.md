# Final Documentation

The CA's final documentation consists of a 2-3 page summary, the GitHub link, the
selected organisation, screenshots/evidence, an individual reflection, and
references and an AI use declaration.

| File | Purpose |
| --- | --- |
| [reflection.md](reflection.md) | My individual technical reflection across the five portfolios. |
| [build_submission.py](build_submission.py) | Builds the LMS submission package from the repository. |

## Building the LMS package

The script needs Python 3.9+, Google Chrome (used headlessly to print the PDF) and
`git`. It takes the name and student ID as arguments, so they are not stored in the
repository. Use letters and digits only, with no spaces:

```bash
python3 final-documentation/build_submission.py --surname Surname --firstname Firstname --student-id 12345678
```

It writes to the git-ignored `submission/` folder:

- `Surname_Firstname_README.txt`, uploaded separately on the form.
- `Surname_Firstname_StudentID.zip`, the zipped folder, containing
  `Surname_Firstname_Documentation.pdf` and `Surname_Firstname_Repository.zip`
  (a snapshot of the tracked files at `HEAD`).

The names follow the LMS rule `Surname_Firstname_DocumentType`, with no spaces. The
script refuses to produce a PDF outside 2-3 pages.

## AI use

The reflection's wording was drafted with AI assistance from the repository's
recorded results and then reviewed by me. This is declared at the end of
[reflection.md](reflection.md), in the "AI use declaration" section of the
documentation PDF, in the submitted README text file, and beside the reflection
link in each portfolio README.
