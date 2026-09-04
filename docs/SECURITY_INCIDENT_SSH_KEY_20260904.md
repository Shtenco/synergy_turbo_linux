# Security incident: committed SSH private key

Date: 2026-09-04

Status: **PRIVATE KEY COMPROMISED — ROTATION/REVOCATION REQUIRED**

## Finding

The `main` branch contained `Linux Ubuntu.ppk` as Git blob:

`e434ef67541f15a2667dab62c4c0d59cfaed85fa`

Inspection confirmed that the file is PuTTY SSH private-key material and that the key file itself declared no encryption.

The private key bytes are intentionally not reproduced in this incident record.

## Security conclusion

The key must be treated as compromised because it existed in repository history. Removing the file from the current tree is necessary but **does not make the old key safe again**.

Required external response:

1. identify every host/account authorized by the corresponding public key;
2. generate a new key pair using current approved algorithms/policy;
3. install the new public key through the host's authorized administrative process;
4. revoke/remove the old public key from every authorized host/account;
5. rotate any dependent credentials if the old private key had privileged access;
6. verify that the old key can no longer authenticate;
7. consider repository-history secret removal according to a human-approved Git history rewrite plan; do not rewrite shared history automatically;
8. review access/audit logs for suspicious use during the exposure window.

## Repository remediation in this branch

- remove `Linux Ubuntu.ppk` from the current tree;
- add `.gitignore` patterns for private-key and local secret material;
- preserve the public key only if it is still useful for identifying/revoking the compromised credential;
- require human review before merge.

## Evidence boundary

This document proves discovery and repository-side remediation preparation only. It does **not** prove key rotation, host revocation, absence of unauthorized use, or history sanitization.
