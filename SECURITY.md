# Security

Little Wins is a single-user example that runs on loopback. It has no login or
authorization. Publishing the source is fine; do not expose a running instance
or its MongoDB port to the internet.

Use a database user scoped to the demo database, keep TLS verification enabled
for remote databases, and store your connection details in a private `.env`
or in server environment variables. Only the placeholder `.env.example` belongs
in version control. If a credential was ever committed or shared, rotate it;
ignoring a file does not remove it from Git history.

Please report security issues privately to the repository owner. Include the
affected file or dependency, the impact, and a way to verify the fix. Do not
include credentials or personal task data in reports.
