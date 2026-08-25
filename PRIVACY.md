# Privacy

Weight Tracker is local-first. By default, wellness data is stored in a SQLite database on the operator's machine and is not sent to a hosted Weight Tracker service.

The database can contain weight, food, exercise, notes, observations, victories, milestones, user identifiers, and activity history. Treat it as private personal information.

AI providers, messaging platforms, remote backups, reverse proxies, or other integrations may transmit user content under their own terms and privacy policies. Those integrations are outside the local core and must be configured by the operator.

Release archives exclude `*.db`, `*.db-wal`, `*.db-shm`, common database backups, and exported data patterns. The installer attempts to restrict the database to the current user (`0600`) on POSIX systems.

Exports contain wellness information. Protect and delete them according to the user's expectations.
