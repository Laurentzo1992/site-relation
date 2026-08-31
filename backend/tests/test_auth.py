def test_register_rejects_invalid_phone(client):
    res = client.post(
        "/auth/register",
        json={
            "email": "bad@example.com",
            "password": "password123",
            "full_name": "Bad Phone",
            "phone": "0102030405",  # missing the leading "+" / country code
            "gender": "homme",
        },
    )
    assert res.status_code == 422


def test_register_rejects_short_password(client):
    res = client.post(
        "/auth/register",
        json={
            "email": "short@example.com",
            "password": "short",
            "full_name": "Short Password",
            "phone": "+22501020304",
            "gender": "homme",
        },
    )
    assert res.status_code == 422


def test_register_login_and_me(client):
    res = client.post(
        "/auth/register",
        json={
            "email": "alice@example.com",
            "password": "password123",
            "full_name": "Alice Kone",
            "phone": "+22501020304",
            "whatsapp": True,
            "gender": "femme",
            "city": "Abidjan",
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["phone"] == "+22501020304"
    assert body["whatsapp"] is True
    assert "hashed_password" not in body

    login = client.post("/auth/login", data={"username": "alice@example.com", "password": "password123"})
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"


def test_login_wrong_password(client, register_user):
    register_user(email="bob@example.com")
    res = client.post("/auth/login", data={"username": "bob@example.com", "password": "wrong-password"})
    assert res.status_code == 401


def test_duplicate_email_rejected(client, register_user):
    register_user(email="dup@example.com")
    res = client.post(
        "/auth/register",
        json={
            "email": "dup@example.com",
            "password": "password123",
            "full_name": "Someone Else",
            "phone": "+22676275726",
            "gender": "homme",
        },
    )
    assert res.status_code == 400
