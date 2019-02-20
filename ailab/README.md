# Launch Benchmark Remotely

You can set up a server and and launch the benchmark run remotely.

## Server Setup

#### Install DJango
```
pip install Django
```

#### Config MySQL Database
- Install MySQL on the server (https://dev.mysql.com/doc/refman/5.7/en/installing.html)
- Create a MySQL database
  - Start MySQL:
  ```
  mysql --user=<username> --password=<password>
  ```
  - In MySQL prompt:
  ```
  CREATE DATABSE <databse_name>
  ```
- In `ailab/settings.py`, speficy `NAME`, `USER` and `PASSWORD` with the name
of the database, username and password of MySQL.
- In the current directory (ailab), run the following commands:
```
python manage.py makemigrations
python manage.py migrate
```

#### Start server
In the current directory (ailab), simply run
```
python manage.py runserver
```
The server should be up and running, ready to receive requests.

## Start Lab (TODO)
`run_lab.py`

## Run Benchmark Remotely (TODO)
`run_remote.py`
