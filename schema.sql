CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    phone_number VARCHAR(15) NOT NULL UNIQUE,
    registration_stage VARCHAR(20) NOT NULL DEFAULT 'new',
    name VARCHAR(50),
    age INT,
    gender CHAR(1),
    county VARCHAR(50),
    town VARCHAR(50),
    level_of_education VARCHAR(50),
    profession VARCHAR(50),
    marital_status VARCHAR(20),
    religion VARCHAR(30),
    ethnicity VARCHAR(30),
    self_description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE match_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    requester_phone VARCHAR(15) NOT NULL,
    requested_phone VARCHAR(15) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (requester_phone) REFERENCES users(phone_number),
    FOREIGN KEY (requested_phone) REFERENCES users(phone_number)
);