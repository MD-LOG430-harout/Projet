import pymysql


def connect_from_env(config):
    return pymysql.connect(
        host=config["MYSQL_HOST"],
        port=int(config.get("MYSQL_PORT", 3306)),
        user=config["MYSQL_USER"],
        password=config["MYSQL_PASSWORD"],
        database=config["MYSQL_DATABASE"],
        charset="utf8mb4",
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
    )

