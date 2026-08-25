# Data portability

Export one user's complete data:

```bash
./weight_tracker --chat-id 123 export user-123.json
```

Merge an export into an initialized database:

```bash
./weight_tracker --chat-id 123 import user-123.json merge
```

Replace all data for the target identity:

```bash
cp weight_tracker.db weight_tracker.db.bak
./weight_tracker --chat-id 123 import user-123.json replace
```

`replace` deletes the target user's existing rows before importing. Use it only after an explicit backup and approval.

Exports contain wellness information. Protect them like the live database.
