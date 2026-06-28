CREATE DATABASE IF NOT EXISTS clients_identite CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS conformite_audit CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS catalogue_offres CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS lignes_services CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS commandes_activations CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON clients_identite.* TO 'cantelcox'@'%';
GRANT ALL PRIVILEGES ON conformite_audit.* TO 'cantelcox'@'%';
GRANT ALL PRIVILEGES ON catalogue_offres.* TO 'cantelcox'@'%';
GRANT ALL PRIVILEGES ON lignes_services.* TO 'cantelcox'@'%';
GRANT ALL PRIVILEGES ON commandes_activations.* TO 'cantelcox'@'%';
FLUSH PRIVILEGES;
