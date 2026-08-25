# Security policy

This repository contains governance templates and CI/reference scripts. A defect can be security-
relevant when it allows a change to appear reviewed, verified, or safe to merge when it is not.

## Reporting

Please **do not publish exploit details in a public Issue** for vulnerabilities that could enable
CI bypass, unsafe merge approval, arbitrary code execution, credential exposure, or another
security boundary failure.

Preferred reporting path:

1. If GitHub shows **Report a vulnerability** / private vulnerability reporting for this
   repository, use it.
2. Otherwise contact the maintainer through an available private channel from the maintainer's
   GitHub profile.
3. If no private channel is available, open a minimal public Issue saying that you have a security
   report and need a private contact path. Do not include reproduction steps or exploit details in
   that Issue.

Include the affected revision, impact, minimum reproduction, and any suggested mitigation. A
report that demonstrates a false-clean or false-approval path is especially useful.

## Scope

Security-relevant examples include:

- a CI or review gate that can return green while skipping the change it claims to inspect;
- untrusted repository content reaching shell execution unsafely;
- permission scopes broader than the workflow requires;
- a merge/review state that can be forged or confused with independent approval;
- a parser failure that silently converts UNKNOWN/invalid state into PASS/VALIDATED.

Normal documentation corrections, feature requests, and non-security script bugs belong in public
Issues or pull requests.

## Supported versions

The default branch is the supported reference. The scripts target **Python 3.10+** and use the
standard library only. Security fixes are made on the default branch; older commits are historical
artifacts and are not maintained as separate release lines.
