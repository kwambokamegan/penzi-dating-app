CREATE TABLE match_searches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    requester_phone VARCHAR(15) NOT NULL,
    age_min INT NOT NULL,
    age_max INT NOT NULL,
    town VARCHAR(50) NOT NULL,
    shown_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE match_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    search_id INT NOT NULL,
    phone_number VARCHAR(15) NOT NULL,
    position INT NOT NULL,
    FOREIGN KEY (search_id) REFERENCES match_searches(id)
);

CREATE TABLE interest_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    requester_phone VARCHAR(15) NOT NULL,
    target_phone VARCHAR(15) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'notified',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
