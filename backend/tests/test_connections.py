from app.models import ConnectionRequest, ConnectionStatus


def _pay_connection_request(client, headers, request_id):
    payment = client.post(
        "/payments/initiate",
        json={"type": "connection_request", "reference_id": request_id},
        headers=headers,
    ).json()
    client.post(f"/payments/{payment['id']}/confirm", headers=headers)


def test_cannot_request_own_ad(client, register_user, publish_ad):
    headers = register_user()
    ad = publish_ad(headers)
    res = client.post("/connections", json={"ad_id": ad["id"]}, headers=headers)
    assert res.status_code == 400


def test_duplicate_request_rejected(client, register_user, publish_ad):
    owner = register_user(email="alice@example.com")
    ad = publish_ad(owner)
    requester = register_user(email="bob@example.com", phone="+22676275726", gender="homme")

    first = client.post("/connections", json={"ad_id": ad["id"]}, headers=requester)
    assert first.status_code == 201
    second = client.post("/connections", json={"ad_id": ad["id"]}, headers=requester)
    assert second.status_code == 400


def test_identity_masked_until_admin_approval(client, register_user, publish_ad, db):
    owner = register_user(email="alice@example.com", full_name="Alice Kone")
    ad = publish_ad(owner)
    requester = register_user(
        email="bob@example.com", full_name="Bob Traore", phone="+22676275726", gender="homme"
    )

    req = client.post("/connections", json={"ad_id": ad["id"]}, headers=requester).json()
    assert req["ad"]["owner"]["full_name"] == "Identite masquee"

    _pay_connection_request(client, requester, req["id"])

    mine = client.get("/connections/mine", headers=requester).json()[0]
    assert mine["status"] == "pending_admin"
    assert mine["ad"]["owner"]["full_name"] == "Identite masquee"

    received = client.get("/connections/received", headers=owner).json()[0]
    assert received["requester"]["full_name"] == "Identite masquee"

    # simulate an admin approving the request directly in the database
    cr = db.get(ConnectionRequest, req["id"])
    cr.status = ConnectionStatus.approved
    db.commit()

    mine_after = client.get("/connections/mine", headers=requester).json()[0]
    assert mine_after["ad"]["owner"]["full_name"] == "Alice Kone"


def test_contact_hidden_until_approved_then_revealed_to_both_parties(
    client, register_user, publish_ad, db
):
    owner = register_user(email="alice@example.com", full_name="Alice Kone")
    ad = publish_ad(owner)
    requester = register_user(
        email="bob@example.com", full_name="Bob Traore", phone="+22676275726", whatsapp=True, gender="homme"
    )

    req = client.post("/connections", json={"ad_id": ad["id"]}, headers=requester).json()
    _pay_connection_request(client, requester, req["id"])

    forbidden = client.get(f"/connections/{req['id']}/contact", headers=requester)
    assert forbidden.status_code == 403

    cr = db.get(ConnectionRequest, req["id"])
    cr.status = ConnectionStatus.approved
    db.commit()

    as_requester = client.get(f"/connections/{req['id']}/contact", headers=requester)
    assert as_requester.status_code == 200
    assert as_requester.json()["full_name"] == "Alice Kone"

    as_owner = client.get(f"/connections/{req['id']}/contact", headers=owner)
    assert as_owner.status_code == 200
    assert as_owner.json()["full_name"] == "Bob Traore"
    assert as_owner.json()["whatsapp"] is True


def test_unrelated_user_gets_404_not_403(client, register_user, publish_ad):
    owner = register_user(email="alice@example.com")
    ad = publish_ad(owner)
    requester = register_user(email="bob@example.com", phone="+22676275726")
    req = client.post("/connections", json={"ad_id": ad["id"]}, headers=requester).json()

    eve = register_user(email="eve@example.com", phone="+22670000000")
    res = client.get(f"/connections/{req['id']}", headers=eve)
    assert res.status_code == 404
