# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 2.x | Yes |
| < 2.0 | No |

## Reporting a vulnerability

Report vulnerabilities by email to **fodorad201@gmail.com** with the subject line
`[personality_questionnaire] Security vulnerability`.

Expect an acknowledgement within **72 hours** and a status update within **7 days**.

## Handling participant data

This package collects human-subject self-reports. If you deploy it:

- Keep the data-collection application on `localhost`. It is not built to be
  internet-facing, and participant consent rarely extends to network transmission.
- Identify participants by a study-local code, never by name.
- The database is yours to secure; this package neither encrypts nor transmits it.
