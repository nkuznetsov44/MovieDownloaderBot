# mysqldump -h 192.168.88.101 -u root -p --no-data --column-statistics=0 CardFillingBot > CardFillingBot_schema.sql
mysqldump -h 192.168.88.101 -u root -p --column-statistics=0 CardFillingBot > CardFillingBot.sql