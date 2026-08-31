def test_search_by_keyword_city_and_gender(client, register_user, publish_ad):
    femme = register_user(email="alice@example.com", full_name="Alice Kone", gender="femme")
    publish_ad(femme, title="Passionnee de musique", description="J'adore la guitare", city="Abidjan")

    homme = register_user(email="bob@example.com", full_name="Bob", phone="+22676275726", gender="homme")
    publish_ad(homme, title="Amateur de cinema", description="Fan de films", city="Ouagadougou")

    by_keyword = client.get("/ads", params={"q": "musique"}).json()
    assert by_keyword["total"] == 1
    assert by_keyword["items"][0]["title"] == "Passionnee de musique"

    by_description_keyword = client.get("/ads", params={"q": "films"}).json()
    assert by_description_keyword["total"] == 1
    assert by_description_keyword["items"][0]["title"] == "Amateur de cinema"

    by_city = client.get("/ads", params={"city": "ouaga"}).json()
    assert by_city["total"] == 1
    assert by_city["items"][0]["city"] == "Ouagadougou"

    by_gender = client.get("/ads", params={"gender": "femme"}).json()
    assert by_gender["total"] == 1
    assert by_gender["items"][0]["owner"]["gender"] == "femme"

    no_match = client.get("/ads", params={"q": "voyage"}).json()
    assert no_match["total"] == 0

    combined = client.get("/ads", params={"gender": "homme", "city": "ouaga"}).json()
    assert combined["total"] == 1


def test_ad_not_public_until_paid(client, register_user, publish_ad):
    headers = register_user(email="alice@example.com", full_name="Alice Kone")
    ad = client.post(
        "/ads",
        json={"title": "Bonjour", "description": "annonce", "looking_for_gender": "homme"},
        headers=headers,
    ).json()
    assert ad["status"] == "pending_payment"

    # not visible on the public listing or detail view yet
    assert client.get("/ads").json()["total"] == 0
    assert client.get(f"/ads/{ad['id']}").status_code == 404


def test_public_ad_never_leaks_owner_name(client, register_user, publish_ad):
    headers = register_user(email="alice@example.com", full_name="Alice Kone")
    ad = publish_ad(headers)

    listing = client.get("/ads").json()
    assert listing["total"] == 1
    owner = listing["items"][0]["owner"]
    assert "full_name" not in owner
    assert owner["gender"] == "femme"
    assert listing["items"][0]["is_new"] is True

    detail = client.get(f"/ads/{ad['id']}").json()
    assert "full_name" not in detail["owner"]
    assert "Alice" not in str(detail)


def test_is_new_becomes_false_once_requested(client, register_user, publish_ad):
    owner = register_user(email="alice@example.com", full_name="Alice Kone")
    ad = publish_ad(owner)

    requester = register_user(email="bob@example.com", full_name="Bob Traore", phone="+22676275726", gender="homme")
    client.post("/connections", json={"ad_id": ad["id"]}, headers=requester)

    detail = client.get(f"/ads/{ad['id']}").json()
    assert detail["is_new"] is False


def test_pagination(client, register_user, publish_ad):
    headers = register_user()
    for i in range(15):
        publish_ad(headers, title=f"Annonce {i}")

    page1 = client.get("/ads", params={"page": 1, "page_size": 12}).json()
    assert len(page1["items"]) == 12
    assert page1["total"] == 15
    assert page1["total_pages"] == 2

    page2 = client.get("/ads", params={"page": 2, "page_size": 12}).json()
    assert len(page2["items"]) == 3


def test_owner_can_see_own_unpublished_ad_via_mine(client, register_user):
    headers = register_user()
    client.post(
        "/ads",
        json={"title": "Brouillon", "description": "d", "looking_for_gender": "homme"},
        headers=headers,
    )
    mine = client.get("/ads/mine", headers=headers).json()
    assert len(mine) == 1
    assert mine[0]["status"] == "pending_payment"


def test_delete_ad_requires_ownership(client, register_user, publish_ad):
    owner = register_user(email="alice@example.com")
    ad = publish_ad(owner)

    other = register_user(email="bob@example.com", phone="+22676275726")
    res = client.delete(f"/ads/{ad['id']}", headers=other)
    assert res.status_code == 404

    res = client.delete(f"/ads/{ad['id']}", headers=owner)
    assert res.status_code == 204
