# Cordy Contibution Guide

Thank you for showing interest in cordy's development 😄. We appreciate all and any help to make cordy better.

## Code of Conduct

We have a code of conduct to ensure appropriate behavior [here](https://github.com/BytesToBits/Cordy/blob/master/.github/CODE_OF_CONDUCT.md)

## First Time Contributors

We will be glad to have you make your first contribution to cordy!
You can check 1st contribution issues [here](https://github.com/BytesToBits/Cordy/contribute) or
you can join the [discord](https://discord.gg/8akycDh) to discuss.

Although we will expect you to know how to use git, so it might it be better to learn how use it.
We will try to handle the rest 😄

## Getting Started

### Issues

If you encounter a bug in cordy then first, search the issue in the issue
tracker. If an issue does not exist then you may create your own issue.
Be sure to provide information for a reproducible example, and **Hide your
Tokens** if you provide code in the issue.

Use suitable title prefixes to categorise issues
For example
 * `[Bug]`
 * `[Request]`
 * `[Bug@vX.Y.Z]`
 * `[Docs]` / `[Documentation]`
 * `[Meta]`

So, a bug report for version `X.Y` looks like `[Bug@vX.Y] A fatal bug.`

### Pull Requests
Pull requests should also use suitable prefixes to categorise PRs
 * `[Feature]` - For a feature PR
 * `[BugFix]` - For a Bug fix
 * `[Docs]` - For a documentation related PR
 * `[Actions]` / `[CI]` - For a CI or Github actions PR
 * `[Workflow]` - For a PR related to development flow, like linting, venv etc.

Not a mandate, but you should link to issues which the PRs resolve.

PRs which do not modify any package code should add `[skip ci]` to their title.

If your issue or PR doesn't receive response then you can get in touch
on [discord](https://discord.gg/8akycDh)

### Typing

Type checking is used in cordy left and right. Hence it is important to be
familiar with typing basics in python. You can find many tutorials on google for the same.

Also use `from __future__ import annotations` to postpone typehint evalution instead of strings.
More info at [PEP 563](https://www.python.org/dev/peps/pep-0563/)

### Versioning

Currently Cordy uses [PEP 440 Semantic Versioning](https://www.python.org/dev/peps/pep-0440/#semantic-versioning)
which is manually incremented and single sourced in `pyproject.toml`

Maybe you can introduce a better versioning workflow 🤷

## Workflow

### Setting up the Environment
The first step to contribute cordy is to setup your local development
environment.

```
$ python script/make_venv .venv/ # windows / (other platforms as well, except the correct python must be used.)

$ script/make_venv .venv/ # Posix-like (may need chmod +x)
```

### Type Checking

It is reccomended that you enable mypy or pyright linting in your IDE

#### Type linting in VSCode
To enable pyright type checking simply install the pylance language server.

To enable mypy linting use the following workspace config.
```json
{
    "python.linting.mypyEnabled": true,
    "python.linting.enabled": true
}
```
#### CLI Type-Checking
If your IDE doesn't support mypy type linting then you can periodically
type check the code over command line by

```
$ mypy -p cordy
```
or
```
$ "script/typec.bat" # On windows

$ script/typec # Posix-like (may need chmod +x)

$ python script/typec # Any platform, In cordy's venv
```

## Style Guide

### Code Style

Cordy uses [PEP 8](https://www.python.org/dev/peps/pep-0008/) code style, all incoming code is expected to be (soft) PEP 8 compliant.

### Commit Messages

* Limit title to less than 50 characters (soft-limit)
* Use of emojis is encouraged.
  * Example = `[➕] Add Object`
  * If using emojis, then ensure that the commit and emoji are atleast slightly related.
* Provide a meaning full title,
* Try to use the changed API's qualifier if char limit isn't reached
* When not writing code / Editing static files add `[skip ci]` to title (*prefixed or suffixed, but the emoji comes before if prefixed*)
* Look at [Atom contributing guide](https://github.com/atom/atom/blob/master/CONTRIBUTING.md#git-commit-messages)
  to get an idea of how to use emojis.

## Tests
Cordy started out as a lib in rapid development but soon the cons of not using
test driven development started catching up. Which is why cordy is slowly
trying to transition to testing. If possible please write tests for your
contributions.
