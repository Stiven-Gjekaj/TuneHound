# Releasing

Each big addition gets a tag and a release on GitHub.

## Versions

A version is `MAJOR.MINOR.PATCH`.
Before 1.0.0, each big addition raises the minor number.
From 1.0.0, a fix raises the patch number and a new function raises the
minor number.
A change that breaks the command line or the file names raises the major
number.

## Cut a release

1. Make sure that `version` in `pyproject.toml` is the version of the
   release.
2. Run the tests and the lint. All of them must pass.

       uv run pytest
       uv run ruff check .
       uv run ruff format --check .

3. Run the program on a real link. Do not only trust the tests.
4. Write the changes of the release at the top of `CHANGELOG.md`.
   Commit it as `docs: add the changelog of X.Y.Z`.
5. Say in the README that the version is out.
   Commit it as `docs: say in the README that X.Y.Z is out`.
6. Build the package. Check that the build has the version of the release.

       uv build

7. Make an annotated tag on that commit and push it:

       git tag -a vX.Y.Z -m "TuneHound X.Y.Z"
       git push origin main vX.Y.Z

8. Make the release on GitHub. Use the entry of the changelog as the text,
   and add the wheel and the source archive from `dist/`.

       gh release create vX.Y.Z dist/* --title "TuneHound X.Y.Z" --notes-file NOTES.md

9. Set the version of the next release in `pyproject.toml` and run
   `uv lock`. Commit it as `chore: set the version of the next release`.

A commit subject names no version number, except in steps 4 and 5.
