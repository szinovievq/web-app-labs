DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS roles;

CREATE TABLE roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    last_name TEXT,
    first_name TEXT NOT NULL,
    middle_name TEXT,
    role_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE SET NULL
);

INSERT INTO roles (name, description) VALUES
('Администратор', 'Полный доступ к управлению системой'),
('Редактор', 'Доступ к изменению данных'),
('Пользователь', 'Ограниченный доступ только для чтения');

INSERT INTO users (login, password_hash, last_name, first_name, middle_name, role_id)
VALUES ('admin', '', 'Иванов', 'Иван', 'Иванович', 1);