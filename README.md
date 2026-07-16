# mycv_rendercv

This repo now contains a first-pass RenderCV version of Joshua Faskowitz's CV in
[Joshua_Faskowitz_CV.yaml](./Joshua_Faskowitz_CV.yaml), plus a dependency-free
BibTeX converter at [scripts/bib_to_rendercv.py](./scripts/bib_to_rendercv.py).

The local bibliography sources live in:

- [bibliography/pubs.bib](./bibliography/pubs.bib)
- [bibliography/posters.bib](./bibliography/posters.bib)

## Workflow

Refresh the generated publication sections after editing either `.bib` file:

```bash
python3 scripts/bib_to_rendercv.py
```

Preview the YAML that would be written:

```bash
python3 scripts/bib_to_rendercv.py --stdout
```

The script updates the block between the `BEGIN/END GENERATED BIBLIOGRAPHY`
markers inside `Joshua_Faskowitz_CV.yaml`. Static CV content stays editable by
hand in the same YAML file.

## Rendering

RenderCV is not installed in this environment yet. Once it is available, the
expected command is:

```bash
rendercv render Joshua_Faskowitz_CV.yaml
```
