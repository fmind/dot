# SQLite Rehearsal

Inspect `sqlite3 --version` and the application's SQLite runtime separately; Python may use a different library. Discover the schema, migration history, journal mode, and writer before altering anything.

```bash
sqlite3 -init /dev/null -batch -bail -readonly app.sqlite '.schema'
sqlite3 -init /dev/null -batch -bail -noheader -list -readonly app.sqlite 'PRAGMA user_version; PRAGMA journal_mode;'
```

Create a fresh protected recovery directory, then use the SQLite backup API or CLI `.backup` for a consistent snapshot. This example writes only the new backup destination; do not reuse a path containing a valuable backup.

```bash
sqlite3 -init /dev/null -batch -bail -readonly app.sqlite ".backup 'recovery/before.sqlite'"
sqlite3 -init /dev/null -batch -bail -noheader -list -readonly recovery/before.sqlite 'PRAGMA integrity_check; PRAGMA foreign_key_check;'
```

The integrity check should return `ok`; the foreign-key check should return no rows. Validate these outcomes explicitly because a command can exit successfully while returning violations. The explicit init/output options keep interactive shell settings from changing the result format. Neither check proves application-level correctness.

1. Restore the snapshot into a disposable location through the same backup mechanism and open it with the old application version. Never replace a live database beneath existing connections.
1. Run the project's migration engine against a separate rehearsal copy. Verify transaction behavior for the installed driver; do not assume DDL, a helper such as `executescript`, and version bookkeeping share one transaction automatically.
1. Enable foreign-key enforcement on the connections that require it, inspect indexes/triggers/views, and follow SQLite's documented table-rebuild procedure when direct ALTER operations cannot preserve the schema. Do not use `writable_schema` or leave integrity constraints disabled to bypass a failure.
1. Compare application records and declared invariants, then exercise rollback or restore and read-back. Include busy writers and an interrupted migration with bounded waits; do not wait forever on a lock.

Do not restore old data over newer writes without a reconciliation decision. Keep recovery files private and apply the project's encryption and retention policy before off-device storage.

Sources: [SQLite online backup](https://www.sqlite.org/backup.html), [ALTER TABLE](https://www.sqlite.org/lang_altertable.html), and [Python sqlite3 transaction control](https://docs.python.org/3/library/sqlite3.html#transaction-control).
