from db import get_connection


# ============================================================
# DATABASE HELPERS
# ============================================================

def _run_query(sql, params=(), one=False):
    """
    Run a SELECT query.

    Returns:
        - one row when one=True
        - all rows when one=False
    """
    conn = get_connection()

    if conn is None:
        raise ConnectionError("Could not connect to the database.")

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)

        if one:
            result = cursor.fetchone()
        else:
            result = cursor.fetchall()

        cursor.close()
        return result

    finally:
        conn.close()


def _run_write(sql, params=()):
    """
    Run an INSERT, UPDATE, or DELETE query.

    Returns the new row ID when available.
    """
    conn = get_connection()

    if conn is None:
        raise ConnectionError("Could not connect to the database.")

    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()

        new_id = cursor.lastrowid

        cursor.close()
        return new_id

    finally:
        conn.close()


# ============================================================
# USERS
# ============================================================

def get_user_by_phone(phone_number):
    """
    Get one user using their phone number.
    """
    return _run_query(
        """
        SELECT *
        FROM users
        WHERE phone_number = %s
        """,
        (phone_number,),
        one=True
    )


def create_user(
    phone_number,
    name,
    age,
    gender,
    county,
    town,
    stage
):
    """
    Create a new user.
    """
    return _run_write(
        """
        INSERT INTO users
        (
            phone_number,
            registration_stage,
            name,
            age,
            gender,
            county,
            town
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            phone_number,
            stage,
            name,
            age,
            gender,
            county,
            town
        )
    )


def save_details(
    phone_number,
    education,
    profession,
    marital_status,
    religion,
    ethnicity,
    stage
):
    """
    Save the user's additional registration details.
    """
    return _run_write(
        """
        UPDATE users
        SET
            level_of_education = %s,
            profession = %s,
            marital_status = %s,
            religion = %s,
            ethnicity = %s,
            registration_stage = %s
        WHERE phone_number = %s
        """,
        (
            education,
            profession,
            marital_status,
            religion,
            ethnicity,
            stage,
            phone_number
        )
    )


def save_description(phone_number, description, stage):
    """
    Save the user's self-description and registration stage.
    """
    return _run_write(
        """
        UPDATE users
        SET
            self_description = %s,
            registration_stage = %s
        WHERE phone_number = %s
        """,
        (
            description,
            stage,
            phone_number
        )
    )


def set_opted_out(phone_number, opted_out):
    """
    Update the user's opt-out status.
    """
    return _run_write(
        """
        UPDATE users
        SET opted_out = %s
        WHERE phone_number = %s
        """,
        (
            1 if opted_out else 0,
            phone_number
        )
    )


# ============================================================
# MATCH SEARCHES
# ============================================================

def find_matches(
    age_min,
    age_max,
    place,
    gender,
    exclude_phone
):
    """
    Find users who match the supplied search criteria.
    """
    return _run_query(
        """
        SELECT phone_number
        FROM users
        WHERE age BETWEEN %s AND %s
          AND gender = %s
          AND phone_number != %s
          AND opted_out = 0
          AND (
              LOWER(county) = LOWER(%s)
              OR LOWER(town) = LOWER(%s)
          )
        ORDER BY id
        """,
        (
            age_min,
            age_max,
            gender,
            exclude_phone,
            place,
            place
        )
    )


def create_search(
    requester_phone,
    age_min,
    age_max,
    place
):
    """
    Create a new match search.
    """
    return _run_write(
        """
        INSERT INTO match_searches
        (
            requester_phone,
            age_min,
            age_max,
            town,
            shown_count
        )
        VALUES (%s, %s, %s, %s, 0)
        """,
        (
            requester_phone,
            age_min,
            age_max,
            place
        )
    )


def add_search_results(search_id, phone_numbers):
    """
    Save the ordered results belonging to a match search.
    """
    if not phone_numbers:
        return

    conn = get_connection()

    if conn is None:
        raise ConnectionError("Could not connect to the database.")

    try:
        cursor = conn.cursor()

        rows = [
            (search_id, phone_number, position)
            for position, phone_number in enumerate(phone_numbers)
        ]

        cursor.executemany(
            """
            INSERT INTO match_results
            (
                search_id,
                phone_number,
                position
            )
            VALUES (%s, %s, %s)
            """,
            rows
        )

        conn.commit()
        cursor.close()

    finally:
        conn.close()


def get_latest_search(requester_phone):
    """
    Get the most recent match search made by a user.
    """
    return _run_query(
        """
        SELECT *
        FROM match_searches
        WHERE requester_phone = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (requester_phone,),
        one=True
    )


def count_search_results(search_id):
    """
    Count how many matches belong to a search.
    """
    row = _run_query(
        """
        SELECT COUNT(*) AS total
        FROM match_results
        WHERE search_id = %s
        """,
        (search_id,),
        one=True
    )

    return row["total"]


def get_search_batch(search_id, offset, limit):
    """
    Get a batch of matches from a saved search.
    """
    return _run_query(
        """
        SELECT
            u.name,
            u.age,
            u.phone_number
        FROM match_results mr
        JOIN users u
            ON u.phone_number = mr.phone_number
        WHERE mr.search_id = %s
        ORDER BY mr.position
        LIMIT %s OFFSET %s
        """,
        (
            search_id,
            limit,
            offset
        )
    )


def set_shown_count(search_id, count):
    """
    Update how many results have already been shown.
    """
    return _run_write(
        """
        UPDATE match_searches
        SET shown_count = %s
        WHERE id = %s
        """,
        (
            count,
            search_id
        )
    )


# ============================================================
# INTEREST REQUESTS
# ============================================================

def create_interest(requester_phone, target_phone):
    """
    Create an interest request.
    """
    return _run_write(
        """
        INSERT INTO interest_requests
        (
            requester_phone,
            target_phone,
            status
        )
        VALUES (%s, %s, 'notified')
        """,
        (
            requester_phone,
            target_phone
        )
    )


def find_recent_interest(
    requester_phone,
    target_phone,
    hours
):
    """
    Find a recent interest request between two users.
    """
    return _run_query(
        """
        SELECT id
        FROM interest_requests
        WHERE requester_phone = %s
          AND target_phone = %s
          AND status = 'notified'
          AND created_at >= NOW() - INTERVAL %s HOUR
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            requester_phone,
            target_phone,
            hours
        ),
        one=True
    )


def get_pending_interest_for(target_phone, hours):
    """
    Get a recent pending interest request for a user.
    """
    return _run_query(
        """
        SELECT
            id,
            requester_phone
        FROM interest_requests
        WHERE target_phone = %s
          AND status = 'notified'
          AND created_at >= NOW() - INTERVAL %s HOUR
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            target_phone,
            hours
        ),
        one=True
    )


def mark_interest_revealed(interest_id):
    """
    Mark an interest request as revealed.
    """
    return _run_write(
        """
        UPDATE interest_requests
        SET status = 'revealed'
        WHERE id = %s
        """,
        (interest_id,)
    )


# ============================================================
# OUTBOX
# ============================================================

def queue_message(phone_number, message):
    """
    Put an outgoing SMS into the outbox.
    """
    return _run_write(
        """
        INSERT INTO outbox
        (
            phone_number,
            message
        )
        VALUES (%s, %s)
        """,
        (
            phone_number,
            message
        )
    )


def get_undelivered(phone_number):
    """
    Get undelivered messages for a phone number.
    """
    return _run_query(
        """
        SELECT
            id,
            message,
            created_at
        FROM outbox
        WHERE phone_number = %s
          AND delivered = 0
        ORDER BY id
        """,
        (phone_number,)
    )


def mark_delivered(ids):
    """
    Mark outgoing messages as delivered.
    """
    if not ids:
        return

    placeholders = ",".join(["%s"] * len(ids))

    return _run_write(
        f"""
        UPDATE outbox
        SET delivered = 1
        WHERE id IN ({placeholders})
        """,
        tuple(ids)
    )


# ============================================================
# FOLLOW-UPS
# ============================================================

def get_users_needing_followup(minutes):
    """
    Find users who have been waiting for details long enough
    to receive a follow-up message.
    """
    return _run_query(
        """
        SELECT phone_number
        FROM users
        WHERE registration_stage = 'awaiting_details'
          AND followup_sent = 0
          AND opted_out = 0
          AND created_at <= NOW() - INTERVAL %s MINUTE
        """,
        (minutes,)
    )


def mark_followup_sent(phone_number):
    """
    Mark a user's registration follow-up as sent.
    """
    return _run_write(
        """
        UPDATE users
        SET followup_sent = 1
        WHERE phone_number = %s
        """,
        (phone_number,)
    )