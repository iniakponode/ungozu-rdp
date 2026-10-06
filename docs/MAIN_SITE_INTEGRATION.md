# Linking the Standalone RDP to iniakpothompson.com

## Objective

Keep the two codebases independently deployable while making the programme a first-class part of the main website experience.

## Main-site changes supplied

The adjacent `iniakpothompson-main-site-link-patch` package updates only:

- public navigation;
- public footer;
- administrator navigation.

It introduces the environment variable:

```text
NEXT_PUBLIC_RDP_URL=https://rdp.iniakpothompson.com
```

## Apply the patch locally

From the root of the current `iniakpothompson.com` Git repository:

```powershell
git status
git apply --check "<PATH_TO_PACKAGE>\iniakpothompson-rdp-links.patch"
git apply "<PATH_TO_PACKAGE>\iniakpothompson-rdp-links.patch"
```

Or run the included `apply-rdp-link-patch.ps1`.

Expected outcome: `git diff` shows only RDP external-link additions in the three navigation/layout files.

## Add the environment variable

Add to the main website frontend production environment:

```text
NEXT_PUBLIC_RDP_URL=https://rdp.iniakpothompson.com
```

Then run the main website's existing validation/build process before committing.

## What not to share

Do not share:

- MariaDB tables;
- JWT signing secrets;
- payment credential encryption keys;
- RDP Alembic migrations;
- RDP participant passwords.

This boundary is what allows both applications to be maintained and rolled back independently.
