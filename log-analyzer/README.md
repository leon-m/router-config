This program displays, imports and analyzes log records, primarily for the firewall channel, |n
produced by the router and stored into the SQLite3 database on NAS. It can fetch log records from |n
different log record sources

## Log Record Sources (`--source`)

Log records can arrive from various sources either as raw log records as reported by  Mikrotik router via syslog facility, or
as the processed log records that have already been converted from the raw log record and stored into the internal storage.
The log source is specified via the argument to the`--source` command line option using the URI syntax:

>    _log-source-type_`://`_log-source-type-details_

The following log source types are supported:

| URI                               | Description  |
|-----------------------------------|--------------|
| `json://`_file-path_              | The source or **raw** records is JSON file |
| `json://sqlite::`_path-to-sqlite-database_ | Runs `sqlite3` export on the specified database to get **raw** records|
| `json://sqlite::`_user_`@`_host_`:`_path-to-sqlite-database_ | Runs `ssh` to the specified host and executes `sqlite` there to get **raw** records|
| `raw://sqlite::`_path-to-sqlite-database_ | The source of **raw** racords is SQLite3 database directly without JSON export |
| `sqlite://`_path-to-sqlite-database_ | Use internal SQLite3 database to fetch **processed** records |
| `postgresql://`_connect-string_`/`_database-name_ |  Use internal PostgreSQL database to fetch **processed** records |

The `json` source type is to read raw records and is expected to contain an array of log record objects produced by
Mikrotik router and exported from the Synolog Log CEnter's database using `sqlite3 --json <select statement>` command. 

To run `ssh` the remote system must have a public key of the user running the program locally. Username/passwotrd logins are not supported.

## Internal database (`--db`)

For the internal database the program can use either SQLite3 or PostgreSQL database engine. The selection, together with connection
details, is done via the value of the `--db` command line parameter, as follows:

| URI                               | Description  |
|-----------------------------------|--------------|
| `sqlite://`_path-to-sqlite-database_ | Use internal SQLite3 database to fetch **processed** records |
| `postgresql://`_connect-string_`/`_database-name_ |  Use internal PostgreSQL database to fetch **processed** records |

### Preparing SQLite3 Database

SQLite database only need creation of schema. Run the following:
```
$ sqlite3 /var/tmp/my-database.db
sqlite> .read sql/db-schema-sqlite.sql
sqlite> ^D
```
That's it. The `/var/tmp/my-database.db` is likely not to exist yet. The `sqlite3` utility will create it. Use it with:
```
$ log-analyzer.py --db sqlite:///var/tmp/my-database.db
```
Use the path tailored to your setup in your environment.

### Preparing PostgreSQL Database

PostgreSQL is an external dabatabase service so it's configuration is slighly more laborous. To start with, you need a running service and an access to the user with administrative proviliges. The `psql` command below assumes that.

The first step is to, as server administrator, create the user that will own the log database and the database itself. Let's assume the username `loguser` and the database name `logdb` (but use names of your choice and better password in real life):
```
$ psql
psql (14.20 (Homebrew))
Type "help" for help.

admin=# CREATE USER loguser WITH ENCRYPTED PASSWORD 'the-password';
admin=# CREATE DATABASE logdb WITH OWNER=logdb;
admin=# ^D
$
```

The next step connect to the database and create the schema:
```
$ psql --username loguser --dbname logdb
psql (14.20 (Homebrew))
Type "help" for help.

logdb=> \i sql/db-schema-postgresql.sql
CREATE TABLE
CREATE TABLE
   ...
CREATE VIEW
logdb=> ^D
$
```

That's it. PostgreSQL database is ready to use. Use it with:
```
$ log-analyzer.py --db postgresql://loguser:the-password@127.0.0.1:5432/logdb ...
```
## Geoip Data
For now the source of geoip data is not configurable, it is fixed to endpoint at `http://ip-api.com/batch`. This endpoint permits
15 requests of 100 IP addresses each per minute. The program is capable of adjusting the request rate as to not exceed the
service's permitted rates.

## Blacklists (`--blacklist`)

| URI                               | Description  |
|-----------------------------------|--------------|
| `bitwire-it://`_path-to-git-repository-clone_ | The source of IP blacklisted addresses |

The program reads the IP address blacklist from the clone of Git repo available on GitHub. To prepare the blacklist clone fetch the
repository from:
```
$ mkdir <repo-checkout-location>
$ cd <repo-checkout-location>
$ git clone https://github.com/bitwire-it/ip_list_fetch.git
```
That's it. The use to import the blacklist occasionally run the program with:
```
$ log-analyzer.py --db <database-uri> --blacklist bitwire-it://<repo-checkout-location>/ip_list_fetch bl-import
```
The first run on the clone will import entire list. Next runs will calculate differences and add ro and remove from the internal database accordingly. To force the import of entire list again remote the `LAST_IMPORTED` tag from the clone.

_Do not, ever, push anything back to remote. Do not pull either as program will do that as necessary._

