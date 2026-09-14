# Contributing

Contributions are welcome, especially platform compatibility tests and clearer failure guidance.

Before opening a pull request:

1. Do not add real infrastructure data or credentials.
2. Preserve the explicit SSH-alias allowlist and `BatchMode=yes` boundary.
3. Never move a password into arguments, environment variables, logs, fixtures, or plaintext files.
4. Add or update tests for behavior changes.
5. Run `python3 -m unittest discover -s tests -v` and `python3 -m compileall -q scripts tests`.

Use synthetic hostnames from RFC 5737 documentation ranges in examples.
