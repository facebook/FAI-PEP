# Launch Benchmark Remotely

You can set up a server and and launch the benchmark run remotely.

## Server Setup

#### Config MySQL Database
- Install MySQL on the server
- Create a MySQL database
- In the current directory (ailab), run
- In `ailab/settings.py`, speficy `NAME`, `USER` and `PASSWORD` with the name
of the database, username and password of MySQL.
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
