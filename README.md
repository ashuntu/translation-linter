# Translation Linter

GitHub action for auto-translating l10n files back into English for easier
review. Also automatically checks for potentially offensive language in
translation files.

Auto-translations provided by [Argos
Translate](https://github.com/argosopentech/argos-translate). Profanity checking
provided by [(Alt) Profanity
Check](https://github.com/dimitrismistriotis/alt-profanity-check).

At the moment it only supports JSON translation files like ARB.

## Usage

[**Example Workflow File**](./.github/workflows/example-action.yaml)

Add the following as a GitHub workflow file (e.g. `.github/workflows/example-action.yaml`):

```yaml
name: YOUR_WORKFLOW_NAME
on:
  workflow_dispatch: 
  pull_request: 
  push:
    branches: [main]

jobs:
  YOUR_JOB:
    name: YOUR_JOB_NAME
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: YOUR_STEP_NAME
        uses: ashuntu/translation-linter
        with:
          # Change this to the directory containing your translations
          # REQUIRED
          translation-dir: "translations"
          # RegEx file mask to match translation files
          # The first group match () should contain the language code
          # OPTIONAL
          file-mask: "app_(.*)\\.arb"
```

## Output

See the [most recent action run](https://github.com/ashuntu/translation-linter/actions) from this repo for an example of the output this action generates.
