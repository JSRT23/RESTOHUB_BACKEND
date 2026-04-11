-- Crea todas las bases de datos necesarias para RestoHub
CREATE DATABASE menu_db;
CREATE DATABASE order_db;
CREATE DATABASE inventory_db;
CREATE DATABASE loyalty_db;
CREATE DATABASE staff_db;
CREATE DATABASE auth_db;
 
GRANT ALL PRIVILEGES ON DATABASE menu_db TO restohub;
GRANT ALL PRIVILEGES ON DATABASE order_db TO restohub;
GRANT ALL PRIVILEGES ON DATABASE inventory_db TO restohub;
GRANT ALL PRIVILEGES ON DATABASE loyalty_db TO restohub;
GRANT ALL PRIVILEGES ON DATABASE staff_db TO restohub;
GRANT ALL PRIVILEGES ON DATABASE auth_db TO restohub;
 