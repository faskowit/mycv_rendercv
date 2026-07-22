# RenderCV CV workflow

This repository contains the RenderCV source for Joshua Faskowitz's CV and a
small, dependency-free Python script that converts BibTeX records into its
publication sections. It is designed to be forked: replace the CV and BibTeX
content, then use the same generation workflow.

## License and content rights

The reusable converter in [`scripts/`](./scripts/) is available under the
[MIT License](./scripts/LICENSE). The CV, bibliography, and rendered outputs
are not covered by that license; see [CONTENT-NOTICE.md](./CONTENT-NOTICE.md)
for their rights notice.

## Prerequisites

- Python 3.10 or newer (the bibliography converter uses only the standard
  library).
- [RenderCV](https://rendercv.com/). The CV YAML references the RenderCV v2.8
  schema, so install a compatible version:

  ```bash
  uv tool install "rendercv[full]==2.8.*"
  ```

  If you do not use `uv`, install the equivalent `rendercv[full]` package with
  your preferred Python environment manager.

## Quick start

```bash
git clone <your-fork-url>
cd mycv_rendercv
python3 scripts/bib_to_rendercv.py
rendercv render Joshua_Faskowitz_CV.yaml
```

Generated files are written to `rendercv_output/` (and intentionally ignored
by Git). The configured render produces PDF, HTML, Markdown, and Typst output.

## Update the bibliography

The bibliography sources are:

- [bibliography/pubs.bib](./bibliography/pubs.bib)
- [bibliography/posters.bib](./bibliography/posters.bib)

After changing either file, regenerate the publication sections:

```bash
python3 scripts/bib_to_rendercv.py
```

Preview the result without modifying the YAML:

```bash
python3 scripts/bib_to_rendercv.py --stdout
```

The script replaces everything between the `BEGIN/END GENERATED
BIBLIOGRAPHY` markers in the CV YAML. Do not hand-edit that generated block;
make bibliography changes in the `.bib` files instead. All other CV content is
edited directly in the YAML file.

### BibTeX inclusion rules

- `@article` entries become **Journal Articles**.
- `@inproceedings` entries become **Peer-Reviewed Conference Proceedings**.
- Records whose `journal` is `bioRxiv`, `bioarXiv`, or `arXiv` become
  **Preprints**.
- Poster entries must include `firstauth` in their comma-separated `keywords`
  field to appear in **Conference Posters (first-author only)**.

Entries are sorted newest first. A DOI is used as a URL when no `url` field is
provided. For conference proceedings, publisher, volume, and page information
are appended to the journal line rather than rendered as an indented summary.
All generated publication sections use reverse-numbered entries; each entry
shows its title, authors, venue, and publication date.

## Adapt this repository for your own CV

1. Rename or replace [Joshua_Faskowitz_CV.yaml](./Joshua_Faskowitz_CV.yaml) and
   update its contact details, sections, and design.
2. Replace `bibliography/pubs.bib` and `bibliography/posters.bib`, or point to
   your own files with `--publications-bib` and `--posters-bib`.
3. Pass your surname to bold your name in generated author lists:

   ```bash
   python3 scripts/bib_to_rendercv.py \
     --yaml Your_Name_CV.yaml \
     --owner-last-name your-surname
   ```

   The default remains `faskowitz`, so Joshua's normal workflow needs no extra
   options. The default CV and bibliography paths are resolved from the
   repository, allowing the default command to run from another directory.
4. If your publication categories differ, update the documented constants near
   the top of [scripts/bib_to_rendercv.py](./scripts/bib_to_rendercv.py):
   `PREPRINT_JOURNALS`, `POSTER_INCLUDE_KEYWORD`, and the section names in
   `render_generated_block`.
5. Render your YAML with `rendercv render Your_Name_CV.yaml`.

## Project layout

```text
Joshua_Faskowitz_CV.yaml  # CV content, styling, and RenderCV settings
bibliography/             # BibTeX sources
scripts/bib_to_rendercv.py # BibTeX-to-RenderCV generator
```

## Before publishing a fork

The example YAML includes real contact information. Replace it before making a
public derivative if you do not intend to publish those details. Forkers may
reuse the MIT-licensed script, but must supply their own CV content and
bibliography or obtain permission to reuse this repository's content.
