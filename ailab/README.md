# Setup Lab and Launch Benchmark Remotely

By setting up a lab, you can set up a server with benchmarking devices connected, and submit benchmarking jobs remotely from another machine. We rely on Django, uWSGI and nginx for setting up the lab. In the README, we'll walk through how to setup the lab server, start the lab, and submit jobs to the lab remotely from another machine.

## Server One-Time Setup

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
- If using Ubuntu, install `python-dev` and `libmysqlclient-dev` for `MySQL-python` (ref: https://codeinthehole.com/tips/how-to-set-up-mysql-for-python-on-ubuntu/)
```
apt-get install python-dev libmysqlclient-dev
```


- Install components for ailab:
```
pip install MySQL-python
pip install django-tables2 "django<2" django-nvd3 django-widget-tweaks django-bootstrap3
```
- In the current directory (ailab), run the following commands:
```
python manage.py makemigrations
python manage.py migrate
```

#### Setup nginx and uWSGI
We will rely on `nginx` and `uWSGI` to serve model files as media files.
Note: the following commands are intended for OS X and are translated from https://uwsgi-docs.readthedocs.io/en/latest/tutorials/Django_and_nginx.html. If you are running a different operating system or want to take a more comprehensive look at the structure, please refer to the link.

0. If using ubuntu, need to install `libpcre3` and `libpcre3-dev` before installing uWSGI:
```
sudo apt-get install libpcre3 libpcre3-dev
```
1. Install uWSGI:
```
pip install uwsgi
```


2. install nginx:
```
brew install nginx
```
3. Create directories for of `sites-enabled` and `sites-available` for nginx:
```
mkdir -p /usr/local/etc/nginx/sites-{enabled,available}
```
4. Modify `ailab_nginx.conf` file:
  - In lines 21, 26 and 32, set appropriate `<path-to-this-directory>`
  - In lines 11 and 13, set appropriate port to `listen` and `server_name`

5. In `setting.py`, add the name of the server to `ALLOWED_HOSTS` list
6. Move the new conf file to nginx's directory and create corresponding links:
```
cp ailab_nginx.conf /usr/local/etc/nginx/sites-available
ln -s /usr/local/etc/nginx/sites-available/ailab_nginx.conf /usr/local/etc/nginx/sites-enabled/
```
7. Update nginx.conf to add the following line in the http section if
it doesn't exit
```
include       /usr/local/etc/nginx/sites-enabled/*.conf;
```

8. Restart nginx service in production setting
```
nginx -s stop
nginx
```

## Start the server
1. Collect static files that Django visualization would use
```
python manage.py collectstatic --clear
```
2. Start uWSGI from this directory in production setting
```
uwsgi --socket :8001 --module ailab.wsgi
```

Now, the server should be up and running, ready to receive requests.


## Start Lab
On server, inside `benchmarking` directory, run:
```
python run_bench.py --lab --claimer_id <claimer_id> --server_addr <server_name> --remote_reporter "<server_name>/benchmark/store-result|oss"
```

## Run Benchmark Remotely
On another machine, inside `benchmarking` directory, invoke the lab by running:
```
python run_bench.py -b <benchmark_file> --remote --devices <devices> --server_addr <server_name>
```
